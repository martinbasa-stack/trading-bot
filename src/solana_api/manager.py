import logging

from src.models import Trade,Balance
from src.wallet.solana import SolanaWalletKeys
from src.solana_api.constants import MAIN_RPC_URL

from .tokens.manager import TokenManager
from .tokens.models import TokenDataClass
from .wallet.executor import SolanaWalletExecutor
from .wallet.balances import get_wallet_balances
from .raydium.swap import RaydiumSwap
from .kamino.lending import KaminoLending
from .utils.round import custom_round

import threading
import copy
from datetime import datetime, timezone
import math

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
        self._kmno = KaminoLending()
        self._open_trades: dict[str, Trade] = {}

        self._lock = threading.Lock()

        self._logger=logging.getLogger("solana").getChild(self.__class__.__name__)

    # Properties
    @property
    def locked(self) -> bool:
        if self.wallet.pub_key:
            return False
        return True
    
    def run_clenup(self):
        """ Remove Error and Finalized (marked with auto_delete) pending tasks"""
        self._executor.run_clenup()

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
                
                resp = self._executor.sign_send(idx, trx, rpc)
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
                    if (self._now() - 20) > self._open_trades[idx].timestamp:
                        self._executor.remove(idx)                        
                        self._open_trades.pop(idx, None)                           
                        return "Error"
                    raise RuntimeError(f"No response recived for '{idx}' response: '{resp}'!")
                
                if resp.trans_stat.err:
                    # Remove from list
                    self._open_trades.pop(idx, None)
                    self._executor.remove(idx)
                    raise RuntimeError(f"Transaction error!")
                
                if resp.trans_stat.confirmation_status.Finalized:
                    trade_closed = copy.copy(self._open_trades[idx])          
                    results = self._executor.get_swap_result(
                        mint_1= self.tokens.get_token(trade_closed.symbol1).mint,
                        mint_2= self.tokens.get_token(trade_closed.symbol2).mint,
                        tx_id=idx
                    )
                    if not results:
                        raise RuntimeError(f"No results recived for {idx}!")
                    
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
            self._logger.error(f"remove error: {repr(e)}")

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
                
                balances =  get_wallet_balances(self.wallet.pub_key, self.tokens)
                print("Solana wallet balances ---------------------------")
                print(balances)
                kmno_dep = self._kmno.get_all_deposits(self.wallet.pub_key)
                print("Solana KAMINO deposits ---------------------------")
                print(kmno_dep)
                if not kmno_dep:
                    return balances
                for s, b in balances.items():
                    t = self.tokens.get_token(s)
                    if t.mint in kmno_dep:
                        b.savings = kmno_dep[t.mint].amount
                        b.total += b.savings

                return balances

        except Exception as e:
            self._logger.error(f"get_balances error: {repr(e)}")

    def savings_update(self, assets: dict[str, Balance]) -> bool:
        """
        Withdraw or deposit to Kamino Savings, depending of token settings and data in Balance data class. 
        Args:
            assets(dict[str, Balance]):
                List of all aseests. Data for withdraw or deposit amount is in Balance data class.
        Returns:
            bool:
                True if any action was triggered. To refresh balance.
        """
        try: 
            action = False
            for symbol, a in assets.items():
                with self._lock:
                    t = self.tokens.get_token(symbol)

                    if not t:
                        continue
                    if not t.en_savings:
                        continue
                    if t.min_deposit > a.savings_wd and a.savings_wd > 0:
                        continue

                    res = self._kmno.get_reserve_basic(t.mint)
                    if not res:
                        continue

                    apy = float(res.get("supplyApy")) * 100
                    if t.min_apy > apy:
                        continue

                if a.savings_wd > 0:
                    self.deposit_savings(t.symbol, a.savings_wd)
                    action = True
                elif a.savings_wd < 0:
                    self.withdraw_savings(t.symbol, abs(a.savings_wd))
                    action = True

            return action
        except Exception as e:
            self._logger.error(f"savings_update error: {e}")

    def pending_savings_trx(self) ->bool:
        for trx in self._executor.pending_trx:
            if "_savings" in trx:
                return True

    def deposit_savings(self, symbol : str, amount :float):
        """
        Wallet has to be unlocked!
        Args:
            symbol(str):
                Symbol for sevings deposit
            amount(float):
                Amount to deposit.
        """
        try:            
            with self._lock:                
                if not self.wallet.pub_key:
                    raise RuntimeError("Wallet locked")
                
                t = self.tokens.get_token(symbol)
                if not t:
                    raise RuntimeError(f"Token: {symbol} not in database")

                trx = self._kmno.generate_deposit_transaction(self.wallet.pub_key, t.mint, amount)
                if not trx:
                    raise RuntimeError(f"No transaction generated by Kamino API")
                
                self._executor.sign_send(f"{symbol}_Deposit_savings", trx, MAIN_RPC_URL, True)

        except Exception as e:
            self._logger.error(f"deposit_savings error: {e}")
    
    def withdraw_savings(self, symbol : str, amount :float):
        """
        Wallet has to be unlocked!
        Args:
            symbol(str):
                Symbol for sevings withdraw
            amount(float):
                Amount to withdraw.
        """
        try:            
            with self._lock:                
                if not self.wallet.pub_key:
                    raise RuntimeError("Wallet locked")
                
                t = self.tokens.get_token(symbol)
                if not t:
                    raise RuntimeError(f"Token: {symbol} not in database")

                trx = self._kmno.generate_withdraw_transaction(self.wallet.pub_key, t.mint, amount)
                if not trx:
                    raise RuntimeError(f"No transaction generated by Kamino API")
                
                self._executor.sign_send(f"{symbol}_Withdraw_savings", trx, MAIN_RPC_URL, True)

        except Exception as e:
            self._logger.error(f"withdraw_savings error: {e}")

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
            q = self.round_down(abs(trade.quantity2), token_in.decimals)
        else: # Sell
            token_in = self.tokens.get_token(trade.symbol1)
            token_out = self.tokens.get_token(trade.symbol2)
            q = self.round_down(abs(trade.quantity1), token_in.decimals)
        
        quant_lamp = int(q * 10 ** token_in.decimals)

        return token_in, token_out, quant_lamp

    
    # ---------------------------------------------------------
    @staticmethod
    def round_down(n, decimals=0):
        multiplier = 10**decimals
        return math.floor(n * multiplier) / multiplier

    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
    