import logging

from src.models import Trade,Balance
from src.wallet.solana import SolanaWalletKeys
from src.solana_api.constants import MAIN_RPC_URL

from .tokens.manager import TokenManager
from .tokens.models import TokenDataClass
from .wallet.executor import SolanaWalletExecutor
from .wallet.balances import get_wallet_balances
from .raydium.swap import RaydiumSwap
from .utils.round import custom_round

import threading
import copy
from datetime import datetime, timezone

class SolanaManager:
    """
    Signe and send transactions. Return actual trade data. Check status of transactions Read balances.
    """
    def __init__(
        self,
        wallet_keys : SolanaWalletKeys,
        settings_get : callable
        ):
        
        """        
        Args:
            wallet_keys(SolanaWalletKeys):
                Solana wallet data.
            price_impact_lim(float, Optional):
                Limit in % of price impact on swap, for trade to be posted.
            slippage_bps(int, Optional):
                Limit in bps (0.01 %) of slipage on swap, for trade to be posted.
            timeout(int, Optional):
                Timeout in s for Raydium to respond.

        Returns:
            str:
                Signature of transaction as string.
        """
        self.wallet = wallet_keys
        self.tokens = TokenManager() 
        self._raydium = RaydiumSwap(
            settings_get=settings_get
            )
        self._executor = SolanaWalletExecutor(wallet_keys)
        self._open_trades: dict[str, Trade] = {}

        self._lock = threading.Lock()

        self._logger=logging.getLogger("solana").getChild(self.__class__.__name__)

    # Properties
    @property
    def locked(self) -> bool:
        if self.wallet.pub_key:
            return False
        return True

    def send_trade(self,idx:str, trade_in : Trade, price_delta_max : float = 1.0) -> Trade:
        """
        Wallet has to be unlocked!
        Send trade if price difference is not to big. If trade is already been recorded as send it will NOT resend.
        Args:
            idx(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
            trade_in(Trade):
                Trade to send
            price_delta_max(float, Optional):
                Maximum price differnce of price in trade and actual price from DEX
        Returns:
            Trade:
                Trade with idx as Send
        """
        try:            
            with self._lock:
                trade = copy.copy(trade_in)
                if idx in self._open_trades:
                    return self._open_trades[idx]
                
                if not self.wallet.keypair:
                    raise RuntimeError("Wallet locked")
                
                #rpc = self._raydium.get_rpc()
                rpc = MAIN_RPC_URL
                token_in, token_out, quant_lamp = self._trade_deconstruct(trade)
                price_raw = self._raydium.get_price(token_in.mint, token_out.mint, quant_lamp)
                if not price_raw:
                    raise ValueError(f"No price data!")    
                price = price_raw * 10**(token_out.decimals - token_in.decimals)
                if trade.quantity1 < 0:
                    price = 1/price # If selling the response price is s2/s1 in trade it is always as s1/s2 example BTC/USDC price is in USDC
                                
                price_delta = round(abs((price - trade.price)/ price) * 100, 2)              
                if price_delta > price_delta_max:
                    raise ValueError(f"Price difference on exchange = {price_delta} % bigger than allowed = {price_delta_max} %")
                
                trx = self._raydium.generate_transaction(token_in.mint, token_out.mint, self.wallet.pub_key, quant_lamp)
                if not trx:
                    raise RuntimeError("No transaction returned!")
                
                resp = self._executor.sign_send_swap(idx, trx, rpc)
                if resp:
                    self._open_trades[idx] = trade
                    return trade  

        except Exception as e:
            self._logger.error(f"send_trade error: {e}")
    
    def is_trade_closed(self,idx:str) -> Trade:
        """
        Check status of transaction "Trade" onchain and updates actual values. If transaction error removes all internal data.
        Args:
            idx(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        Returns:
            Trade:
                Trade with idx as signature and actual ammounts, and fee as commision.
        """
        try:
            with self._lock:
                if idx not in self._open_trades:
                    return None
                
                resp = self._executor.get_status(idx)
                if not resp:
                    raise RuntimeError("No response recived!")
                
                if resp.trans_stat.err:
                    # Remove from list
                    self._open_trades.pop(idx, None)
                    self._executor.remove(idx)
                    return None
                
                if resp.trans_stat.confirmation_status.Finalized:
                    trade_closed = copy.copy(self._open_trades[idx])          
                    results = self._executor.get_swap_result(
                        mint_1= self.tokens.get_token(trade_closed.symbol1).mint,
                        mint_2= self.tokens.get_token(trade_closed.symbol2).mint,
                        tx_id=idx
                    )
                    if not results:
                        raise RuntimeError("No results recived!")
                    
                    trade_closed.idx = resp.signature            
                    trade_closed.quantity1 = custom_round(results.amount_1)
                    trade_closed.quantity2 = custom_round(results.amount_2)
                    trade_closed.price = custom_round(results.price)
                    trade_closed.commision_symbol = "SOL"
                    trade_closed.commision = custom_round(float(float(results.fee_lamports) / 10 ** self.tokens.get_token("SOL").decimals) )               
                    return trade_closed
            
            return None
        
        except Exception as e:
            self._logger.error(f"is_trade_closed error: {repr(e)}")
    
    # Remove trade when it was saved
    # -------------------------------------------------------
    def remove(self,idx:str):
        """
        Remove trade from local data.
        Args:
            idx(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        """
        try:
            with self._lock:
                if idx not in self._open_trades:
                    return                
                
                # Remove from list
                self._open_trades.pop(idx, None)
                self._executor.remove(idx)   
        
        except Exception as e:
            self._logger.error(f"is_trade_closed error: {repr(e)}")

    def get_balances(self) -> dict[str, Balance]:
        """
        Wallet has to be unlocked!
        Returns:
            dict[str, Balance]:
                Dictionary of Balances ready for asset manager.
        """
        try:            
            with self._lock:                
                if not self.wallet.pub_key:
                    raise RuntimeError("Wallet locked")
                
                return get_wallet_balances(self.wallet.pub_key, self.tokens)                

        except Exception as e:
            self._logger.error(f"sign_send error: {e}")
    
    def is_tradable(self, s1, s2) -> bool:
        """
        Check if pair is tradable.
        Args:
            s1(str):
                Symbol1 of trading pair.
            s2(str):
                Symbol2 of trading pair.
        Returns:
            bool:
                Result
        """
        try:
            with self._lock:
                t1 = self.tokens.get_token(s1)
                t2 = self.tokens.get_token(s2)
                if not self._raydium.get_routes(t1.mint, t2.mint):
                    return False
                return True
        
        except Exception as e:
            self._logger.error(f"is_tradable error: {e}")
            return False

    def _trade_deconstruct(self, trade: Trade) -> tuple[TokenDataClass, TokenDataClass, int]:
        if trade.quantity1 > 0: # BUY
            token_in = self.tokens.get_token(trade.symbol2)
            token_out = self.tokens.get_token(trade.symbol1)
            q = abs(trade.quantity2)
        else: # Sell
            token_in = self.tokens.get_token(trade.symbol1)
            token_out = self.tokens.get_token(trade.symbol2)
            q = abs(trade.quantity1)
        
        quant_lamp = int(q * 10 ** token_in.decimals)

        return token_in, token_out, quant_lamp

    
    
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
    