from .models import IndicatorResult

from src.market_history import IntervalData,FearGread
from src.settings import StrategyConfig, IndicatorConfig, StrategyManager
from ..trades import AverageSum

import threading
from datetime import datetime, timezone
from typing import Tuple 
import logging

import talib as ta

# IndicatorCompute Class (short-living)
# ----------------------------------------------------------------------
class IndicatorCompute:
    """ 
    (short-living) Class for analayzing indicators.
        Has multiple class dependencies!
    """
    def __init__(self, 
                 strategies_obj : StrategyManager,
                 get_hist_table:callable, 
                 get_all_avg: callable,
                 get_close: callable,
                 fear_gread_get : callable
                 ):     
        """ 
        Args:
            strategies_obj(StrategyManager):
                object of StrategyManager /settings
            get_hist_table(callable(pair, interval)):
                get kLine historical data of pair and interval from MarketHistoryManager /market_history
            get_all_avg(callable(id)):
                get average entry, cost and exit from TradeAnalyzer class /trades
            get_close(callable(pair)):
                get last close value fro stream data StreamData class from /binance/stream
            fear_gread_get(callable):
                Get value of Fear and Gread
        """
        self._get_hist_table: callable = get_hist_table
        self._strategies_obj : StrategyManager = strategies_obj
        self._get_last_close : callable = get_close
        self._all_avg : callable = get_all_avg
        self._get_fng: callable = fear_gread_get
        self._pair:str = ""
        self._asset_manager = None
        self._last_close: float = 0.0
        self._avg_cost : AverageSum = AverageSum()
        self._avg_entry :AverageSum = AverageSum()
        self._avg_exit :AverageSum = AverageSum()
        #threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================  
    # return the factor and trade limit from buy indicators
    # ------------------------------------------------------------------  
    def get_buy_compute(self, strategy_id:int) -> Tuple[float, int, bool]:
        """
        Args:
            strategy_id(int): 
                Strategy ID.
        Returns:
            Tuple[float, int, bool]:
                sum_factor , sum_weight, enable_trade
        """
        try:
            indicators_result = self.get_buy_list(strategy_id)
            with self._lock:                
                if indicators_result:
                    sum_factor , sum_weight, enable_trade = self._comput_result_list(self._asset_manager.min_weight_buy,indicators_result)
                else:
                    sum_factor = 0
                    sum_weight = 0
                    enable_trade = True
                sum_factor = min(sum_factor, self._asset_manager.buy_max_factor)

            return sum_factor , sum_weight, enable_trade
        
        except Exception as e: 
            self._logger.error(f"get_buy_compute() error: {e}")
        
    # return the factor and trade limit from sell indicators
    # ------------------------------------------------------------------  
    def get_sell_compute(self, strategy_id) -> Tuple[float, int, bool]:
        """
        Args:
            strategy_id(int):
                Strategy ID.
        Returns:
            Tuple [float, float, bool]:
                sum_factor , sum_weight, enable_trade
        """
        try:
            indicators_result = self.get_sell_list(strategy_id)        
            with self._lock:
                if indicators_result:                    
                    sum_factor , sum_weight, enable_trade = self._comput_result_list(self._asset_manager.min_weight_sell, indicators_result)
                else:
                    sum_factor = 0
                    sum_weight = 0
                    enable_trade = True
                sum_factor = min(sum_factor, self._asset_manager.sell_max_factor)
            return sum_factor , int(sum_weight), enable_trade
    
        except Exception as e: 
            self._logger.error(f"get_sell_compute() error: {e}")

    
    # return the resault list of buy indicators
    # ------------------------------------------------------------------  
    def get_buy_list(self, strategy_id) -> list[IndicatorResult]:
        """
        Args:
            strategy_id(Any):
                Strategy ID.
        Returns:
            list[IndicatorResult]:
                Returns of BUY indicators resault after compute.
        """
        try:
            with self._lock:
                self._populate_instance_vars(strategy_id)
                indicators_config : list[IndicatorConfig] = self._strategies_obj.get_buy_indic_config(strategy_id)
                
                return self._generate_result_list(indicators_config)
            
        except Exception as e: 
            self._logger.error(f"get_buy_list() ID strategy {strategy_id} error: {e}")
    
    # return the resault list of sell indicators
    # ------------------------------------------------------------------  
    def get_sell_list(self, strategy_id:int) -> list[IndicatorResult]:
        """
        Args:
            strategy_id(Any): 
                Strategy ID.
        Returns:
            list[IndicatorResult]:
                Returns of SELL indicators resault after compute.
        """
        try:
            with self._lock:
                self._populate_instance_vars(strategy_id)
                indicators_config : list[IndicatorConfig] = self._strategies_obj.get_sell_indic_config(strategy_id)
                return self._generate_result_list(indicators_config)
            
        except Exception as e: 
            self._logger.error(f"get_sell_list() ID strategy {strategy_id} error: {e}")

    # Helpers
    # ==================================================================
    # populate instance variables call befor doing opperatins
    # ------------------------------------------------------------------
    def _populate_instance_vars(self, strategy_id):
        self._load_strategy_data(strategy_id)
        avg_entry, avg_cost, avg_exit = self._all_avg(strategy_id)
        self._avg_entry = avg_entry
        self._avg_cost = avg_cost
        self._avg_exit = avg_exit
        if not avg_entry:
            self._avg_entry = AverageSum()
        if not avg_cost:
            self._avg_cost = AverageSum()
        if not avg_exit:
            self._avg_exit = AverageSum()
        self._last_close = self._get_last_close(self._pair)

    # get pair form strategy
    # ------------------------------------------------------------------
    def _load_strategy_data(self, strategy_id):
        strategy : StrategyConfig = self._strategies_obj.get_by_id(strategy_id)
        if not strategy:
            return None
        self._pair = f"{strategy.symbol1}{strategy.symbol2}"
        self._asset_manager = strategy.asset_manager
    
    # run trough list of configuration and creat list of resaults
    # ------------------------------------------------------------------
    def _generate_result_list(self, indicators_config : list[IndicatorConfig]) -> list[IndicatorResult]:        
        result_list = []
        try:
            for ind_config in indicators_config:
                match ind_config.type_i:
                    case "SMA":
                        result = self._ma_indicator(ind_config)
                    case "EMA":
                        result = self._ma_indicator(ind_config)
                    case "BB":
                        result = self._bb_indicator(ind_config)
                    case "RSI":
                        result = self._rsi_indicator(ind_config)
                    case "ROC":
                        result = self._roc_indicator(ind_config)
                    case "ADX":
                        result = self._adx_indicator(ind_config)
                    case "F&G":
                        result = self._fng_indicator(ind_config)
                    case "AvrageCost":
                        result = self._average_indicator(self._avg_cost.avg, "Average Cost", ind_config)
                    case "AvrageEntry":
                        result = self._average_indicator(self._avg_entry.avg, "Average Entry", ind_config)
                    case "AvrageExit":
                        result = self._average_indicator(self._avg_exit.avg, "Average Exit", ind_config)
                    case "Price":
                        result = self._price_indicator(ind_config)
                
                result_list.append(result)
                
            return result_list
        
        except Exception as e: 
            self._logger.error(f"_generate_result_list() indicator Type {ind_config.type_i} error: {e}")
    
    # get atable from marked data history
    # ------------------------------------------------------------------
    def _hist_table(self, pair, interval) -> IntervalData:    
        hist_table : IntervalData = self._get_hist_table(pair,interval)        
        return hist_table
     
    # price indicators
    # ------------------------------------------------------------------        
    def _price_indicator(self, config:IndicatorConfig) -> IndicatorResult:  
        ind_out = self._last_close

        result = self._ind_compute(ind_out, config.trigger, ind_out, config)
        result.dis_text = f"Price | Trigger"

        return result
       
    # Average Entry, Exit and Cost indicators
    # ------------------------------------------------------------------        
    def _average_indicator(self, avg, text, config:IndicatorConfig) -> IndicatorResult:  
        ind_out = avg
        trigger = self._last_close

        result = self._ind_compute(ind_out, trigger, ind_out, config)
        result.dis_text = f"{text} | Price"

        if avg == 0: #At start of trading there is no avrage
            result.enable_trade = True
            result.weight = config.weight

        return result

    # Fwear and Gread indicators
    # ------------------------------------------------------------------        
    def _fng_indicator(self, config:IndicatorConfig) -> IndicatorResult:  
        fng : float = self._get_fng()
        ind_out = fng
        result = self._ind_compute(100, config.trigger, ind_out, config)
        result.dis_text = f"Fear & Gread | Trigger"

        return result
    
    # ADX volatilyty 
    # ------------------------------------------------------------------        
    def _adx_indicator(self, config:IndicatorConfig) -> IndicatorResult:
        hist_table = self._hist_table(self._pair, config.interval)
        
        if not hist_table:
            return self._empty_result(config)
        
        close = hist_table.close     
        high = hist_table.high     
        low = hist_table.low
        
        timeperiode = config.value1
        if len(close) <= timeperiode: 
            return self._empty_result(config)

        ta_list = ta.ADX(high, low, close, timeperiode) 
        ind_out = round(ta_list[-1],2)

        config.block_trade_offset = 0
        result = self._ind_compute(100, config.trigger, ind_out, config)
        result.dis_text = f"{config.type_i} {config.value1}x {config.interval} | Trigger"

        return result
    
    # Rate Of Change indicator
    # ------------------------------------------------------------------        
    def _rsi_indicator(self, config:IndicatorConfig) -> IndicatorResult:
        hist_table = self._hist_table(self._pair, config.interval)
        
        if not hist_table:
            return self._empty_result(config)
        
        close = hist_table.close     
                
        timeperiode = config.value1

        if len(close) <= timeperiode: 
            return self._empty_result(config)

        ta_list = ta.RSI(close,timeperiode)   
        ind_out = round(ta_list[-1],2)

        config.block_trade_offset = 0
        result = self._ind_compute(100, config.trigger, ind_out, config)
        result.dis_text = f"{config.type_i} {config.value1}x {config.interval} | Trigger"

        return result

    # Rate Of Change indicator
    # ------------------------------------------------------------------        
    def _roc_indicator(self, config:IndicatorConfig) -> IndicatorResult:
        hist_table = self._hist_table(self._pair, config.interval)
        
        if not hist_table:
            return self._empty_result(config)
        
        close = hist_table.close     

        if len(close) <1:
            return self._empty_result(config)
        
        timeperiode = config.value1
        if len(close) <= timeperiode: 
            return self._empty_result(config)

        ta_list = ta.ROC(close,timeperiode)   
        ind_out = round(ta_list[-1],4)

        config.block_trade_offset = 0
        result = self._ind_compute(1, config.trigger, ind_out, config)
        result.dis_text = f"{config.type_i} {config.value1}x {config.interval} | Trigger"

        return result
    
    # moving averadge index for both EMA and SMA
    # ------------------------------------------------------------------        
    def _ma_indicator(self, config:IndicatorConfig) -> IndicatorResult:
        hist_table = self._hist_table(self._pair, config.interval)
        
        if not hist_table:
            return self._empty_result(config)
        
        close = hist_table.close
        
        timeperiode = config.value1
        if len(close) <= timeperiode: 
            return self._empty_result(config)

        if config.type_i == "SMA":        
            ta_list = ta.SMA(close,timeperiode)
        else:
            ta_list = ta.EMA(close,timeperiode)        
        ind_out = ta_list[-1]

        trigger, dis_text = self._trigger_select(close, config) 
            
        result = self._ind_compute(ind_out, trigger, ind_out, config)
        result.dis_text = dis_text

        return result
    
    # Boolinger bands nbdev-up-down both at default 2
    # ------------------------------------------------------------------        
    def _bb_indicator(self, config:IndicatorConfig) -> IndicatorResult:
        hist_table = self._hist_table(self._pair, config.interval)
        
        if not hist_table:
            return self._empty_result(config)
        
        close = hist_table.close  
        
        timeperiode = config.value1
        if len(close) <= timeperiode: 
            return self._empty_result(config)

        upper, middle, lower = ta.BBANDS(close,timeperiode)   
        match config.output_select:    
            case "Upper":        
                ind_out = upper[-1]
            case "Lower":        
                ind_out = lower[-1]
            case _:        
                ind_out = middle[-1]

        trigger = self._last_close

        result = self._ind_compute(100, trigger, ind_out, config)
        result.dis_text = f"BB {config.output_select} {config.value1}x {config.interval} | Price"

        return result

    # compute results for all indicators after values are set
    # ------------------------------------------------------------------      
    def _ind_compute(self, divider, trigger, ind_out, config:IndicatorConfig) -> IndicatorResult: 
        trigger_offset = (config.block_trade_offset /100.0 +1) * trigger

        weight = self._weight_logic(ind_out, trigger_offset, config)

        delta = self._delta(divider , ind_out, trigger)
        factor =  delta * config.factor

        if config.comparator == "Below":
            factor = -factor

        factor_limit = min(factor, config.max_f)
        factor_limit = max(factor_limit, 0.0)
        if not config.enable: factor_limit = 0.0

        return IndicatorResult(weight=int(weight), 
                               enable_trade=bool(weight==config.weight), 
                               delta=float(round(delta,2)), 
                               out_val=float(ind_out),
                               trigger=float(trigger),
                               trigger_offset=float(trigger_offset),
                               factor=float(round(factor,2)),
                               factor_limit=float(round(factor_limit,2)))
    
    # select trigger type for the ones that have option
    # ------------------------------------------------------------------   
    def _trigger_select(self, value, config:IndicatorConfig) -> Tuple[float, str]:
        sel = config.trigger_select
        dis_text = f"{config.type_i} {config.value1}x {config.interval} | {sel} "
        
        # Reduce the value of timeperiod for error protection on Backtester
        timeperiode = config.trigger
        if len(value) < timeperiode:   
            timeperiode = len(value) -1

        match sel:
            case "SMA":
                ta_list = ta.SMA(value, timeperiode)  
                trigg_val = ta_list[-1]
                dis_text +=f"{timeperiode}x {config.interval}"
            case "EMA":
                ta_list = ta.EMA(value, timeperiode)
                trigg_val = ta_list[-1]
                dis_text +=f"{timeperiode}x {config.interval}"
            case _: #For price
                trigg_val = self._last_close
        
        return float(trigg_val) , dis_text
    

    # compute the factors and check trade enable
    # ------------------------------------------------------------------
    @staticmethod
    def _comput_result_list(min_weight : int, indicators_result : list[IndicatorResult]) -> Tuple[float,int, bool ]:
        sum_factor = 0.0
        sum_weight = 0
        for result in indicators_result:
            sum_factor += result.factor_limit
            sum_weight += result.weight
        
        trade_enable = min_weight <= sum_weight
        
        return float(sum_factor), int(sum_weight),  trade_enable
    
    @staticmethod
    def _empty_result(config : IndicatorConfig) -> IndicatorResult:
        return IndicatorResult(
            enable_trade=True, weight=config.weight, dis_text=f"{config.type_i} {config.value1} No data"            
        )

    # calculate delta
    # ------------------------------------------------------------------
    @staticmethod
    def _delta(divider, val_to_compre, trigger) -> float:
        return (val_to_compre - trigger)/divider if divider != 0 else 1#Calc price change from trigger -Down +Up 
        
    # compare values depending on comparator and return weight
    # ------------------------------------------------------------------
    @staticmethod
    def _weight_logic(val_to_compre,trigger_offset, config:IndicatorConfig) -> int:
        if config.comparator == "Above": # Check side for logic "Above" -> BLOCK if price below trigger 
            if val_to_compre >= trigger_offset: 
                return config.weight  #Add weight to enable trade
        else:
            if val_to_compre <= trigger_offset: 
                return config.weight #Add weight to enable trade
        return 0

    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())       