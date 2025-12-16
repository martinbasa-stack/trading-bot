from typing import Dict
from .models import Balance

import copy
import threading
import logging

# AssetManager Class (long-living)
# ----------------------------------------------------------------------
class AssetManager:
    """ (long-living) Class for storing user asset balances """
    def __init__(self, 
                 get_by_id:callable ): 
        """ 
        Args:
            get_by_id(callable(id)): 
                get all strategy parameters by ID from StrategyManager /settings
        """        
        self._get_strategy_by_id = get_by_id
        # key = symbol (e.g. "USDT"), value = Assets object
        self._assets: Dict[str, Balance] = {}
        # threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)
    
    # Public 
    # ==================================================================
    # Update ALL balances (full refresh)
    # new_balances: list[dict] or list[Assets]
    # ------------------------------------------------------------------
    def update(self, new_balances : Dict[str, Balance]):
        """
        Clear all previous values and write new recived ones.
        Args:
            new_balances(Dict[str, Balance]): 
                dictionary with symbol as key and Balance as value
        """
        try:
            if new_balances is None:
                return
            
            with self._lock:
                self._assets.clear()
                for key, item in new_balances.items():
                    self._assets[key] = item

        except Exception as e: 
            self._logger.error(f"update() error: {e}")

    # Get available balance for an asset
    # ------------------------------------------------------------------
    def get_available(self, symbol: str) -> float:
        """        
        Args:
            symbol(str): 
                Symbol
        Returns:
            float:
                Ammount of available assets.
        """
        try:            
            with self._lock:
                asset = self._assets.get(symbol)
                return asset.available if asset else 0.0
    
        except Exception as e: 
            self._logger.error(f"get_available() error: {e}")

    # Check if we have enough balance
    # ------------------------------------------------------------------
    def has_enough(self, symbol: str, amount: float) -> bool:
        try:            
            with self._lock:
                asset = self._assets.get(symbol)
                if not asset:
                    return False
                return asset.available >= amount
    
        except Exception as e: 
            self._logger.error(f"has_enough() error: {e}")

    # Optional getter
    # ------------------------------------------------------------------
    def get_asset(self, symbol: str) -> Balance:
        """        
        Args:
            symbol(str): 
                Symbol
        Returns:
            Balance:
                Returne all balance data of a symbol.
        """
        try:
            with self._lock:
                asset = self._assets.get(symbol)
                if not asset:
                    return Balance(0,0,0)
                return Balance(
                    asset.available,
                    asset.locked,
                    asset.total
                )
        
        except Exception as e: 
            self._logger.error(f"get_asset() error: {e}")
    
    # Optional getter
    # ------------------------------------------------------------------
    def get_all(self) -> list[Balance]:
        """
        Returns:
            list[Balance]:
                Returne all balance data in memory.
        """
        try:
            with self._lock:
                return copy.copy(self._assets)
            
        except Exception as e: 
            self._logger.error(f"get_asset() error: {e}")
    
    # Helpers
    # ==================================================================   
