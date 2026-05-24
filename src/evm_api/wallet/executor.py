import logging

from src.wallet.evm import EvmWalletKeys

from .models import PendingTrans, SwapResult
from .constants import STAT_CONFIRMED,STAT_ERROR,STAT_FINALIZED,STAT_PROCESSED, STAT_SAVED


import base64
import threading
from datetime import datetime, timezone

from web3 import Web3 

class EvmWalletExecutor:
    """
    Signe and send transactions. Check status of transactions Read balances.
    """
    def __init__(
        self,
        wallet_keys : EvmWalletKeys,
        rpc:str
    ):        
        """
        Args:
            wallet_keys(EvmWalletKeys):
                Evm wallet data.
        """
        self._wallet = wallet_keys
        self._rpc = rpc

        self._logger=logging.getLogger("evm").getChild(self.__class__.__name__)
        self._pending: dict[str, PendingTrans] = {}

        self._lock = threading.Lock()

    @property
    def pending_trx(self):
        return self._pending

    def sign_send(self,tx_id:str, tx:dict, auto_delete: bool = False) -> str:
        """
        Signs prebuilt VersionedTransaction and submits it onchain.
        Args:
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
            tx(dict):
                transaction as dictionary
            rpc(str):
                RPC URL for transaction.
        Returns:
            str:
                Signature of transaction as string.
        """
        try:
            
            with self._lock:
                if tx_id in self._pending:
                    return self._pending[tx_id].hash
                account = self._wallet.account
                if not account:
                    raise RuntimeError("Wallet locked")
                
                w3 = Web3(Web3.HTTPProvider(self._rpc))                
                assert w3.is_connected(), f"Failed to connect to {self._rpc}"

                nonce = w3.eth.get_transaction_count(self._wallet.pub_address)

                tx["nonce"] = nonce
                if "from" not in tx:
                    tx["from"] = self._wallet.pub_address
                if "chainId" not in tx:
                    tx["chainId"] = w3.eth.chain_id
                if "gas" not in tx:
                    tx["gas"] = 21000

                # Sign 
                signed_tx = account.sign_transaction(tx)

                # Send
                tx_hash = w3.eth.send_raw_transaction(signed_tx)
                resp = tx_hash.hex()
                self._pending[tx_id] = PendingTrans(
                    hash = resp,
                    sent_at = self._now(),
                    status = "sent",
                    auto_delete= auto_delete,
                    trans_stat=None
                )
                return self._pending[tx_id].hash
            
        except Exception as e:
            self._logger.error(f"sign_send error: {repr(e)}")

    # Check status of transaction and removed finished ones
    def run_clenup(self):
        """
        Remove Error and Finalized (marked with auto_delete) pending tasks
        """
        with self._lock:
            for trx_id in list(self._pending.keys()):
                pending_stat = self._check_by_id(trx_id)
                self._logger.info(f"run_clenup pending {trx_id} status: {pending_stat}")
                if not pending_stat:
                    #self._pending.pop(trx_id, None)
                    continue
                status = pending_stat.status
                if status == STAT_ERROR:
                    self._pending.pop(trx_id, None)
                elif status == STAT_FINALIZED and pending_stat.auto_delete:
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
                signature = self._pending[tx_id].hash
                resp =  self._load_transaction(signature)
                if not resp:
                    raise RuntimeError(f"No response from load_transaction signature '{signature}'")
                
                return self._extract_data_from_trx(resp, mint_1, mint_2, tx_id)
            
        except Exception as e:
            self._logger.error(f"get_swap_result error: {repr(e)}")
        
    def remove(self, tx_id: str):
        """
        Removes the transaction from pending.

        Args:
            tx_id(str):
                transaction ID (Strategy ID since only one trade at the time is logical)
        """
        with self._lock:
            if tx_id not in self._pending:
                return
            if not self._pending[tx_id]:
                return
            self._pending[tx_id].status = STAT_SAVED
            self._pending.pop(tx_id, None)

    def _check_by_id(self, tx_id: str) -> PendingTrans:
        try:

            if tx_id not in self._pending:
                raise RuntimeError(f"'{tx_id}' is not a pending transaction!")
            if not self._pending[tx_id]:
                raise RuntimeError(f"'{tx_id}' has no transaction data!")
            
            hash = self._pending[tx_id].hash
            stat = self._load_confirmation(hash)

            if stat is None:
                raise RuntimeError(f"'{tx_id}' has no transaction data!")
            
            if stat.err:
                self._pending[tx_id].status = STAT_ERROR
            
            if stat.confirmation_status == TransactionConfirmationStatus.Confirmed:            
                self._pending[tx_id].status = STAT_CONFIRMED
            if stat.confirmation_status == TransactionConfirmationStatus.Processed:            
                self._pending[tx_id].status = STAT_PROCESSED
            if stat.confirmation_status == TransactionConfirmationStatus.Finalized:            
                self._pending[tx_id].status = STAT_FINALIZED
            
            self._pending[tx_id].trans_stat = stat
            
            return self._pending[tx_id]
        
        except Exception as e:
            self._logger.error(f"check_by_id error: {repr(e)}")

    def _load_confirmation(self, hash_str: str) -> dict:
        
        w3 = Web3(Web3.HTTPProvider(self._rpc))                
        assert w3.is_connected(), f"Failed to connect to {self._rpc}"
        resp = w3.eth.get_transaction(hash_str)        
        
        if resp is None:
            raise RuntimeError(f"check_confirmation: No response recived for hash: '{hash_str}'!")
        
        return resp
           

    def _load_transaction(self, signature_str: str) -> GetTransactionResp:

        resp = client.get_transaction(s,encoding="jsonParsed", max_supported_transaction_version=0)

        if resp is None:
            raise RuntimeError(f"load_transaction: No response recived for signature: '{signature_str}'!")
        
        return resp
           
    
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
            self._logger.error(f"extract_data_from_trx error: {repr(e)}")
   
    
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
