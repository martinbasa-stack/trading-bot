import logging

from src.wallet.solana import SolanaWalletKeys

from .models import PendingTrans, SwapResult

from solana.rpc.api import Client
from solders.transaction import VersionedTransaction
from solana.rpc.types import TxOpts
from solders.solders import TransactionStatus, Signature, GetTransactionResp

import base64
import threading
from datetime import datetime, timezone

from src.solana_api.constants import MAIN_RPC_URL



class SolanaWalletExecutor:
    """
    Signe and send transactions. Check status of transactions Read balances.
    """
    def __init__(
        self,
        wallet_keys : SolanaWalletKeys
    ):        
        """
        Args:
            wallet_keys(SolanaWalletKeys):
                Solana wallet data.
        """
        self._wallet = wallet_keys
        self._logger=logging.getLogger("solana").getChild(self.__class__.__name__)
        self._pending: dict[str, PendingTrans] = {}
        self._clients :dict[str: Client] = {}
        self._clients[MAIN_RPC_URL] = Client(MAIN_RPC_URL)

        self._lock = threading.Lock()



    def sign_send_swap(self,tx_id:str, tx_base64:str, rpc:str) -> str:
        """
        Signs prebuilt VersionedTransaction and submits it onchain.
        Args:
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
            tx_base64(str):
                transaction already serialised only signature and deserialising needed
            rpc(str):
                RPC URL for transaction.
        Returns:
            str:
                Signature of transaction as string.
        """
        try:
            
            with self._lock:
                if tx_id in self._pending:
                    return self._pending[tx_id].signature
                keypair = self._wallet.keypair
                if not keypair:
                    raise RuntimeError("Wallet locked")
                
                raw_tx = base64.b64decode(tx_base64)
                tx = VersionedTransaction.from_bytes(raw_tx)
                # Sign
                singed_tx = VersionedTransaction(tx.message, [keypair])
                client = self._get_client(rpc)
                # Send
                resp = client.send_raw_transaction(
                    bytes(singed_tx), 
                    opts=TxOpts(skip_preflight=False, max_retries=5)
                )
                self._pending[tx_id] = PendingTrans(
                    signature = str(resp.value),
                    sent_at = self._now(),
                    status = "sent",
                    trans_stat=None
                )
                return self._pending[tx_id].signature
        except Exception as e:
            self._logger.error(f"sign_send error: {repr(e)}")

    # Check status of transaction and removed finished ones
    def run_clenup(self):
        """
        Remove ERROR pending tasks.
        """
        with self._lock:
            for trx_id in list(self._pending.keys()):
                pending_stat = self._check_by_id(trx_id)
                if not pending_stat:
                    self._pending.pop(trx_id, None)
                    continue
                status = pending_stat.status
                if status == "error":
                    self._pending.pop(trx_id, None)
        
    def get_status(self, tx_id:str) ->PendingTrans:
        """
        Get status of signature
        Args:
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        Returns:
            PendingTrans:
                Status object of send transaction.
        """
        with self._lock:
            return self._check_by_id(tx_id)
        
    
    def get_swap_result(self, mint_1, mint_2, tx_id:str) ->SwapResult:
        """
        Get swap results
        Args:
            mint_1(str):
                mint addres of symbol1
            mint_2(str):
                mint addres of symbol2
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        Returns:
            SwapResult:
                Resault of actual onchain swap after it is Finalised
        """
        try:
            with self._lock:
                if tx_id not in self._pending:
                    return
                signature = self._pending[tx_id].signature
                resp =  self._load_transaction(signature)
                if not resp:
                    return
                
                return self._extract_data_from_trx(resp, mint_1, mint_2, tx_id)
            
        except Exception as e:
            self._logger.error(f"get_swap_result error: {repr(e)}")
        
    def remove(self, tx_id: str):
        """
        Removes the trade from open trades.

        Args:
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        """
        with self._lock:
            if tx_id not in self._pending:
                return
            if not self._pending[tx_id]:
                return
            self._pending[tx_id].status = "Saved"
            self._pending.pop(tx_id, None)

    def _check_by_id(self, tx_id: str) -> PendingTrans:
        try:

            if tx_id not in self._pending:
                return None
            if not self._pending[tx_id]:
                return None
            
            signature = self._pending[tx_id].signature
            stat = self._load_confirmation(signature)

            if stat is None:
                return None
            
            if stat.err:
                self._pending[tx_id].status = "error"
            
            if stat.confirmation_status.Confirmed:            
                self._pending[tx_id].status = "Confirmed"
            if stat.confirmation_status.Processed:            
                self._pending[tx_id].status = "Processed"
            if stat.confirmation_status.Finalized:            
                self._pending[tx_id].status = "Finalized"
            
            self._pending[tx_id].trans_stat = stat
            
            return self._pending[tx_id]
        
        except Exception as e:
            self._logger.error(f"check_by_id error: {repr(e)}")

    def _load_confirmation(self, signature_str: str) -> TransactionStatus:
        try:
            client = self._get_client()
            s= Signature.from_string(signature_str)
            resp = client.get_signature_statuses([s],search_transaction_history=True)
            stat = resp.value[0]

            if stat is None:
                return None
            
            return stat
           
        except Exception as e:
            self._logger.error(f"check_confirmation error: {repr(e)}")

    def _load_transaction(self, signature_str: str) -> GetTransactionResp:
        try:
            client = self._get_client()
            s = Signature.from_string(signature_str)
            resp = client.get_transaction(s,encoding="jsonParsed", max_supported_transaction_version=0)

            if resp is None:
                return None
            
            return resp
           
        except Exception as e:
            self._logger.error(f"_load_transaction error: {e}")
    
    def _extract_data_from_trx(self, resp: GetTransactionResp, mint_1, mint_2, tx_id):
        try:
            if not resp.value:
                return
            meta = resp.value.transaction.meta
            pre = meta.pre_token_balances        
            post = meta.post_token_balances

            for in_, post_b in enumerate(post):
                pre_b = pre[in_]
                dec = int(pre_b.ui_token_amount.decimals)
                if str(mint_1) == str(pre_b.mint):
                    amount_1 = float(int(pre_b.ui_token_amount.amount) / 10**dec) - float(int(post_b.ui_token_amount.amount) / 10**dec)
                    
                if str(mint_2) == str(pre_b.mint):
                    amount_2 = float(int(pre_b.ui_token_amount.amount) / 10**dec) - float(int(post_b.ui_token_amount.amount) / 10**dec)

            return SwapResult(
                tx_id=tx_id,
                mint_1 = mint_1,
                amount_1 = amount_1,
                mint_2 = mint_1,
                amount_2 = amount_2,
                price = abs(amount_2/amount_1) if amount_1 != 0 else 0.0,
                fee_lamports = meta.fee,
                slot =  resp.value.slot,
                timestamp= resp.value.block_time    
            )
        except Exception as e:
            print(resp)
            self._logger.error(f"extract_data_from_trx error: {repr(e)}")
    
    def _get_client(self, rpc: str = MAIN_RPC_URL) -> Client:
        if rpc not in self._clients:
            self._clients[rpc] = Client(rpc)
        return self._clients[rpc]
    
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
    