from .models import Balance
from src.settings.strategies import StrategyManager

import copy
import threading
import logging

# AssetManager Class (long-living)
# ----------------------------------------------------------------------
class AssetManager:
    """ (long-living) Class for storing user asset balances """
    def __init__(
            self,
            strategies_obj: StrategyManager,
            strat_type: str,
            get_price: callable
            ): 
        """ 
        """
        self._type = strat_type
        self._get_price: callable = get_price
        self._strategies_obj :StrategyManager = strategies_obj
        self._assets: dict[str, Balance] = {}
        # threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)
    
    # Public 
    # ==================================================================
    # Update ALL balances (full refresh)
    # new_balances: list[dict] or list[Assets]
    # ------------------------------------------------------------------
    def update(self, new_balances : dict[str, Balance]):
        """
        Clear all previous values and write new recived ones.
        Args:
            new_balances(dict[str, Balance]): 
                dictionary with symbol as key and Balance as value
        """
        try:
            if new_balances is None:
                return
            
            with self._lock:
                self._assets.clear()
                for key, item in new_balances.items():
                    self._assets[key] = item

                self._fill_savings_wd()

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

    # Check if have enough balance
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
                    return Balance()
                return asset
        
        except Exception as e: 
            self._logger.error(f"get_asset() error: {e}")
    
    # Optional getter
    # ------------------------------------------------------------------
    def get_all(self) -> dict[str, Balance]:
        """
        Returns:
            dict[str, Balance]:
                Returne all balance data in memory.
        """
        try:
            with self._lock:
                return copy.copy(self._assets)
            
        except Exception as e: 
            self._logger.error(f"get_asset() error: {e}")
    
    def _fill_savings_wd(self):
        self._reserve_for_trades()

        for _, a in self._assets.items():
            savings_wd = a.available - a.trade_reserve
            if savings_wd < 0:
                if abs(savings_wd) > a.savings:
                    if a.min_trade_reserve > a.savings:
                        savings_wd = 0
                    else:
                        savings_wd = - a.savings * 0.99

            a.savings_wd = savings_wd

    # Helpers
    # ==================================================================   
    # Check trade reserves
    def _reserve_for_trades(self):
        strategies = self._strategies_obj.get_all()
        for s in strategies:
            if s.type_s != self._type:
                continue
            if s.asset_manager.paper_t:
                continue
            if not s.run:
                continue

            
            if s.symbol2 in self._assets:
                b = self._assets[s.symbol2]
                reserve = (s.asset_manager.buy_base * (1+ (s.asset_manager.buy_max_factor / 100)))
                b.trade_reserve = max(reserve, b.trade_reserve)
                b.min_trade_reserve = max(s.asset_manager.buy_min, b.min_trade_reserve)

            if s.symbol1 in self._assets:
                b = self._assets[s.symbol1]
                price = self._get_price(f"{s.symbol1}{s.symbol2}")
                reserve = (s.asset_manager.sell_base * (1+ (s.asset_manager.sell_max_factor / 100))) / price
                b.trade_reserve = max(reserve, b.trade_reserve)
                b.min_trade_reserve = max(s.asset_manager.sell_min / price, b.min_trade_reserve)
            
            
