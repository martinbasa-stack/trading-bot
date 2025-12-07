from .models import AssetManagerResult

from src.settings import AssetManagerConfig, StrategyConfig
from ..trades import AverageSum

import copy
import threading
import logging

# AssetManager Class (short-living)
# ----------------------------------------------------------------------
class AssetAnalyzer:
    """ (short-living) Class for analayzing the balance has multiple class dependencies! """
    def __init__(self, 
                 get_by_id:callable,
                 get_all_avg: callable,
                 get_available_balance : callable,
                 get_close :callable
                 ):        
        """ 
        Args:
            get_by_id(callable(id)):
                get all strategy parameters by ID from StrategyManager /settings

            get_all_avg(callable(id)):
                get average entry, cost and exit from TradeAnalyzer class /trades

            get_available_balance(callable(pair, id)):
                get available balance from AssetManager class /
                
            get_close(callable(pair)):
                get last close value fro stream data StreamData class from /binance/stream
        """
        #functions
        self._get_strategy_by_id = get_by_id
        self._get_all_avg = get_all_avg
        self._get_available_balance = get_available_balance
        self._get_close = get_close
        # manager calculations vars
        self._config: AssetManagerConfig = None
        self._avg_entry :AverageSum = None
        self._avg_cost :AverageSum = None
        self._avg_exit :AverageSum = None
        self._buy_factor: float = 0.0
        self._sell_factor :float = 0.0
        self._to_buy: float = 0.0
        self._to_sell: float = 0.0
        self._s1_available_balance: float = 0.0
        self._s2_available_balance :float = 0.0
        self._last_close : float = 0.0
        
        # threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)
    
    # Public 
    # ==================================================================
    # Update ALL balances (full refresh)
    # new_balances: list[dict] or list[Assets]
    # ------------------------------------------------------------------
    def get_compute(self, strategy_id, buy_factor, sell_factor) -> AssetManagerResult:
        """ 
        Args:
            strategy_id(Any): 
                strategy IDx n umber
            buy_factor(float): 
                calculated buy factor from indicators
            sell_factor(float): 
                calculated sell factor from indicators
        """
        try:
            with self._lock:
                self._buy_factor = buy_factor
                self._sell_factor = sell_factor
                self._populate_instance_vars(strategy_id)

                match self._config.target:
                    case "Account":
                        self._target_account()
                    case "Trades":
                        self._target_trades()

                #Limit toBuy and toSell to the availabla assets
                self._to_buy  = min(self._to_buy , self._s2_available_balance) 
                self._to_sell = min(self._to_sell, self._s1_available_balance * self._last_close)
                
            return AssetManagerResult(
                to_buy=self._to_buy,
                available_s2=self._s2_available_balance,
                s2_balance_ok=bool(self._to_buy >= self._config.buy_min),
                to_sell=self._to_sell,
                available_s1=self._s1_available_balance,
                s1_balance_ok=bool(self._to_sell >= self._config.sell_min)
            )
    
        except Exception as e: 
            self._logger.error(f"get_compute() error: {e}")
    
    # Helpers
    # ==================================================================   
    # populate instance variables call befor doing opperatins
    # ------------------------------------------------------------------
    def _populate_instance_vars(self, strategy_id):        
        strategy : StrategyConfig = self._get_strategy_by_id(strategy_id)
        self._config = copy.deepcopy(strategy.asset_manager)
        pair = f"{strategy.symbol1}{strategy.symbol2}"
        self._last_close = self._get_close(pair)
        if self._last_close ==0:
            return
        self._to_buy = self._config.buy_base * ((self._buy_factor /100) +1)
        self._to_sell = self._config.sell_base * ((self._sell_factor /100) +1)

        self._avg_entry, self._avg_cost, self._avg_exit = self._get_all_avg(strategy_id)
              
        self._s2_available_balance = self._to_buy
        self._s1_available_balance = self._to_sell / self._last_close

        if not self._config.paper_t:
            self._s1_available_balance = self._get_available_balance(strategy.symbol1) *0.99
            self._s2_available_balance = self._get_available_balance(strategy.symbol2) *0.99

        # If max limit is 0 than it is unlimited
        if self._config.symbol_index == 1:
            if self._config.max_spend_limit ==0:
                self._config.max_spend_limit = self._to_buy * 10
        else:
            if self._config.max_spend_limit ==0:
                self._config.max_spend_limit = self._to_sell * 10
    
    def _target_account(self):
        if self._config.symbol_index == 1: #Save symbol 1 and spend symbol 2
            #Limit spending of asset
            self._s2_available_balance = self._config.max_spend_limit + self._avg_cost.sum2 # sumS2 is negative when spent
            #Limit minimum account ballance
            if self._config.percent: #if true calculate in percantage
                #Calculate all Buys minus pecentage of all buys
                self._s1_available_balance -= (self._avg_entry.sum1 * self._config.min_save_limit / 100) 
            else: #else calculate in absolute values
                self._s1_available_balance -= self._config.min_save_limit
        else: #Save Symbol 2 and spend Symbol 1
            #Limit minimum account ballance 
            if self._config.percent: #if true calculate in percantage
                #Calculate all Sells minus pecentage of all Sell
                self._s2_available_balance -= (abs(self._avg_exit.sum2) * self._config.min_save_limit / 100) 
            else:
                self._s2_available_balance -= self._config.min_save_limit
            #Limit spending of asset
            self._s1_available_balance = self._config.max_spend_limit + self._avg_cost.sum1 # sumS1 is negative when spent

    def _target_trades(self):
        if self._config.symbol_index  == 1: #Save symbol 1 and spend symbol 2
            #Limit spending of asset
            self._s2_available_balance = self._config.max_spend_limit + self._avg_cost.sum2 # sumS2 is negative when spent
            #Limit minimum saved
            if self._config.percent: #if true calculate in percantage
                #Calculate all trades minus pecentage of all buys
                self._s1_available_balance = self._avg_cost.sum1 - (self._avg_entry.sum1 * self._config.min_save_limit / 100) 
            else: #else calculate in absolute values
                self._s1_available_balance = self._avg_cost.sum1 - self._config.min_save_limit
        else: #Save Symbol 2 and spend Symbol 1
            #Limit minimum saved 
            if self._config.percent: #if true calculate in percantage
                #Calculate all Sells minus pecentage of all Sell
                self._s2_available_balance =  self._avg_cost.sum2 - (abs(self._avg_exit.sum2) * self._config.min_save_limit / 100)
            else:
                self._s2_available_balance =  self._avg_cost.sum2 - self._config.min_save_limit  #SumS2 is negative when spent
            #Limit spending of asset 
            self._s1_available_balance = self._config.max_spend_limit + self._avg_cost.sum1 #sumS1 is negative when spent
        
