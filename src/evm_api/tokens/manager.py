from .models import TokenDataClass
from .token_data import EvmTokenData
from ..utils.storage import save_json, load_json

import logging
from pathlib import Path
import shutil
import threading
import copy

from web3 import Web3

class EvmTokenManager:
    """
    Manage token data. Save to file, get from network.
    """
    def __init__(
        self,
        file_path,
        rpc
    ):        
        self._token_d_obj : EvmTokenData = EvmTokenData()
        self._file_path = Path(file_path)
        self._rpc = rpc
        self._tokens_data: dict[str,TokenDataClass] = {}
        self._lock = threading.Lock()        
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("evm").getChild(self.__class__.__name__) 

        self._load()


    @property
    def tokens(self) -> dict[str,TokenDataClass]:
        with self._lock:
            return self._tokens_data
        
    # Internal JSON I/O
    # ==================================================================
    def _load_json(self) -> dict[str : TokenDataClass]:
        #Load strategies from disk or initialize empty file.
        
        try:

            if not self._file_path.exists():
                raise FileNotFoundError(self._file_path)
            if self._file_path.exists():
                backup = self._file_path.with_suffix(".bak")
                shutil.copy2(self._file_path, backup)

            raw = load_json(self._file_path)
            return raw
        except Exception as e:
            self._logger.error(f"Error loading token data: {e}")

    def _save_json(self):
        #Write strategies to disk with safe logging.
        try:
            json_ready = [self._data_class_to_dict(x) for _, x in self._tokens_data.items()]
            save_json(self._file_path, json_ready)

        except Exception as e:
            self._logger.error(f"Error saving token data: {e}")


    # Public 
    # ================================================================== 
    # save to file
    # ---------------------------------------------------------  
    def save(self):
        with self._lock:
            self._save_json() 

    def delete(self, symbol: str):
        with self._lock:
            if symbol in self._tokens_data:
                self._tokens_data.pop(symbol, None)
        
        self.save()

    # Add new token to data
    # ---------------------------------------------------------
    def new_token(self, mint_str: str, en_savings: bool = False, min_deposit: float = 10.0, min_apy: float = 0.1) -> TokenDataClass:
        """
        Args:
            mint_str (str): SPL token mint address        
        """
        try:
            with self._lock:
                web3 = Web3(Web3.HTTPProvider(self._rpc))
                assert web3.is_connected(), f"Failed to connect to {self._rpc}"

                d: TokenDataClass = self._token_d_obj.load_token(web3, mint_str)
                d.en_savings = en_savings
                d.min_deposit = min_deposit
                d.min_apy = min_apy
                self._tokens_data[d.symbol] = d

            self.save()
            return d
        except Exception as e:
            self._logger.error(f"new_token() error: {e}")

    # Get token data
    # ---------------------------------------------------------
    def get_token(self, symbol: str) -> TokenDataClass:
        """
        Args:
            symbol (str): Token symbol
        Returns:
            TokenDataClass:
        """
        try:            
            with self._lock:
                if symbol in self._tokens_data:
                    return copy.copy(self._tokens_data[symbol] )
        except Exception as e:
            self._logger.error(f"get_token() error: {e}")
            
    # Get token data from mint
    # ---------------------------------------------------------
    def get_token_by_mint(self, mint: str) -> TokenDataClass:
        """
        Args:
            symbol (str): Token symbol
        Returns:
            TokenDataClass:
        """
        try:            
            with self._lock:
                for _, d  in self._tokens_data.items():
                    if d.mint == str(mint):
                        return d
                return False
        except Exception as e:
            self._logger.error(f"get_token() error: {e}")
  
    # Helpers
    # ==================================================================      
    # load
    # ---------------------------------------------------------  
    def _load(self):
        raw = self._load_json()
        if not raw:
            return
        for x in raw:
            self._tokens_data[x["symbol"]] = self._dict_to_data_class(x) 
        
    # Data converters
    # ---------------------------------------------------------
    @staticmethod
    def _dict_to_data_class(d:dict) -> TokenDataClass:
        return TokenDataClass(
                mint= d["mint"],
                decimals= d["decimals"],
                supply= d["supply"],
                name=d["name"],
                symbol= d["symbol"],
                uri= d["uri"],
                en_savings= d.get("en_savings"),
                min_deposit= d.get("min_deposit"),
                min_apy= d.get("min_apy")
            )
        
    @staticmethod   
    def _data_class_to_dict(s: TokenDataClass) -> dict:
        return {
            "mint" : s.mint,
            "decimals" : s.decimals,
            "supply" : s.supply,
            "name": s.name,
            "symbol": s.symbol,
            "uri" : s.uri,
            "en_savings" : s.en_savings,
            "min_deposit" : s.min_deposit,
            "min_apy" : s.min_apy,
        }