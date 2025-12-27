from .models import IndicatorValues

from src.market_history import IntervalData, FearGread
from src.settings import StrategyConfig, IndicatorConfig, StrategyManager

import threading
from datetime import datetime, timezone
from typing import Tuple 
import logging
import math

import talib as ta

# IndicatorChart Class (short-living)
# ----------------------------------------------------------------------
class IndicatorChart:
    """ 
    (short-living) Class for preparing indicators for charts.
    """
    def __init__(self, 
                 strategies_obj : StrategyManager,
                 get_hist_table:callable,
                 get_fng_hist : callable
                 ):     
        """ 
        Args:
            strategies_obj(StrategyManager):
                object of StrategyManager /settings
            get_hist_table(callable(pair, interval)):
                get kLine historical data of pair and interval from MarketHistoryManager /market_history
            get_fng_hist(callable()):
                get Fear and Gread history
        """
        self._get_hist_table: callable = get_hist_table
        self._get_fng_hist: callable = get_fng_hist
        self._strategies_obj : StrategyManager = strategies_obj
        self._pair:str = ""
        #threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================  
        
    # return the resault list of buy indicators
    # ------------------------------------------------------------------  
    def get_solo_ind_list(self, strategy_id) -> list[IndicatorValues]:
        """
        Args:
            strategy_id(Any):
                Strategy ID.
        Returns:
            list[IndicatorValues]:
                Returns indicators for charting that have their own chart.
        """
        try:
            with self._lock:
                self._load_strategy_data(strategy_id)
                indicators_s : list[IndicatorConfig] = self._strategies_obj.get_sell_indic_config(strategy_id)
                indicators_b : list[IndicatorConfig] = self._strategies_obj.get_buy_indic_config(strategy_id)
                indicators = self._merge_unique_indicators(indicators_s, indicators_b)
                
                return self._generate_solo_value_list(indicators)
            
        except Exception as e: 
            self._logger.error(f"get_buy_list() error: {e}")
    
    # return the resault list of sell indicators
    # ------------------------------------------------------------------  
    def get_integrated_indc(self, strategy_id:int) -> list[IndicatorValues]:
        """
        Args:
            strategy_id(Any): 
                Strategy ID.
        Returns:
            list[IndicatorValues]:
                Returns indicators for charting that ar integrated to candle chart.
        """
        try:
            with self._lock:
                self._load_strategy_data(strategy_id)
                indicators_s : list[IndicatorConfig] = self._strategies_obj.get_sell_indic_config(strategy_id)
                indicators_b : list[IndicatorConfig] = self._strategies_obj.get_buy_indic_config(strategy_id)
                indicators = self._merge_unique_indicators(indicators_s, indicators_b)

                return self._generate_integrated_value_list(indicators)
            
        except Exception as e: 
            self._logger.error(f"get_integrated_indc() error: {e}")

    # Helpers
    # ==================================================================
    # get pair form strategy
    # ------------------------------------------------------------------
    def _load_strategy_data(self, strategy_id):
        strategy : StrategyConfig = self._strategies_obj.get_by_id(strategy_id)
        if not strategy:
            return None
        self._pair = f"{strategy.symbol1}{strategy.symbol2}"
    
    # run trough list of configuration and creat list of resaults
    # ------------------------------------------------------------------
    def _generate_solo_value_list(self, indicators_config : list[IndicatorConfig]) -> list[IndicatorValues]:
        result_list = []
        for ind_config in indicators_config:            
            result = None
            match ind_config.type_i:
                case "RSI":
                    result = self._rsi_indicator(ind_config)
                case "ROC":
                    result = self._roc_indicator(ind_config)
                case "ADX":
                    result = self._adx_indicator(ind_config)
                case "F&G":
                    result = self._fng_indicator(ind_config)

            if result:
                result_list.append(result)
        return result_list
    
        # run trough list of configuration and creat list of resaults
    # ------------------------------------------------------------------
    def _generate_integrated_value_list(self, indicators_config : list[IndicatorConfig]) -> list[IndicatorValues]:
        result_list = []
        for ind_config in indicators_config:
            result = None
            match ind_config.type_i:
                case "SMA":
                    result = self._ma_indicator(ind_config)
                case "EMA":
                    result = self._ma_indicator(ind_config)
                case "BB":
                    result = self._bb_indicator(ind_config)

            if result:
                result_list.append(result)
        return result_list
    
    
    # get atable from marked data history
    # ------------------------------------------------------------------
    def _hist_table(self, pair, interval) -> IntervalData:    
        hist_table : IntervalData = self._get_hist_table(pair,interval)        
        return hist_table
     
    # ADX volatilyty  
    # ------------------------------------------------------------------        
    def _adx_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        hist_table = self._hist_table(self._pair, config.interval)
        close = hist_table.close     
        high = hist_table.close     
        low = hist_table.close     

        ta_list = ta.ADX(high, low, close, config.value1)
        ta_chart = self._indicator_to_chart_data_drop_nan(hist_table.time_close, ta_list)
        
        return IndicatorValues(
            i_type=config.type_i,
            interval=config.interval,
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,
            val1= ta_chart,
            val2=None,
            val3=None,
            val4=None
        )

        
    # Fear & Gread 
    # ------------------------------------------------------------------        
    def _fng_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        fng_table : list[FearGread] = self._get_fng_hist()
        
        ta_chart = self._fng_to_chart(fng_table)
        
        return IndicatorValues(
            i_type=config.type_i,
            interval="1d",
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,
            val1= ta_chart,
            val2=None,
            val3=None,
            val4=None
        )
    
    # Rate Of Change indicator
    # ------------------------------------------------------------------        
    def _rsi_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        hist_table = self._hist_table(self._pair, config.interval)
        close = hist_table.close     

        ta_list = ta.RSI(close,config.value1)
        ta_chart = self._indicator_to_chart_data_drop_nan(hist_table.time_close, ta_list)

        return IndicatorValues(
            i_type=config.type_i,
            interval=config.interval,
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,
            val1=ta_chart,
            val2=None,
            val3=None,
            val4=None
        )

    # Rate Of Change indicator
    # ------------------------------------------------------------------        
    def _roc_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        hist_table = self._hist_table(self._pair, config.interval)
        close = hist_table.close     
        
        ta_list = ta.ROC(close,config.value1)
        ta_chart = self._indicator_to_chart_data_drop_nan(hist_table.time_close, ta_list)

        return IndicatorValues(
            i_type=config.type_i,
            interval=config.interval,
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,
            val1=ta_chart,
            val2=None,
            val3=None,
            val4=None
        )
    
    # moving averadge index for both EMA and SMA
    # ------------------------------------------------------------------        
    def _ma_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        hist_table = self._hist_table(self._pair, config.interval)
        close = hist_table.close
        if config.type_i == "SMA":        
            ta_list = ta.SMA(close,config.value1)
        else:
            ta_list = ta.EMA(close,config.value1)        

        ta_chart = self._indicator_to_chart_data_drop_nan(hist_table.time_close, ta_list)

        return IndicatorValues(
            i_type=config.type_i,
            interval=config.interval,
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,            
            val1=ta_chart,
            val2=None,
            val3=None,
            val4=None
        )
    
    # Boolinger bands nbdev-up-down both at default 2
    # ------------------------------------------------------------------        
    def _bb_indicator(self, config:IndicatorConfig) -> IndicatorValues:
        hist_table = self._hist_table(self._pair, config.interval)
        close = hist_table.close     
        upper, middle, lower = ta.BBANDS(close,config.value1)   
        
        ta_chart_upper = self._indicator_to_chart_data_drop_nan(hist_table.time_close, upper)
        ta_chart_middle = self._indicator_to_chart_data_drop_nan(hist_table.time_close, middle)
        ta_chart_lower = self._indicator_to_chart_data_drop_nan(hist_table.time_close, lower)

        return IndicatorValues(
            i_type=config.type_i,
            interval=config.interval,
            in1=config.value1,
            in2=config.value2,
            in3=config.value3,
            in4=config.value4,
            val1=ta_chart_upper,
            val2=ta_chart_middle,
            val3=ta_chart_lower,
            val4=None
        )

    @staticmethod
    def _merge_unique_indicators(list_a, list_b):
        seen = set()
        unique = []

        for cfg in list_a + list_b:
            key = (
                cfg.type_i,
                cfg.interval,
                cfg.value1,
                cfg.value2,
                cfg.value3,
                cfg.value4,
            )

            if key not in seen:
                seen.add(key)
                unique.append(cfg)

        return unique
    
    @staticmethod
    def _indicator_to_chart_data_drop_nan(x, y):
        return [
            {"x": int(ts), "y": float(val)}
            for ts, val in zip(x, y)
            if val is not None and not math.isnan(val)
        ]
    
    @staticmethod
    def _fng_to_chart(data : list[FearGread] ):
        return [
            {"x": int(val.timestamp * 1000), "y": float(val.value)}
            for val in data
        ]

    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())       