from src.settings import  StrategyConfig, StrategyManager
from src.market_history import IntervalData
from src.strategy import TradeAnalyzer, AverageSum, Trade
from src.constants import INDICATOR_INTERVAL_LIST

from .indicators import IndicatorChart

import threading
from datetime import datetime, timezone
import logging
from typing import Tuple 

# FormatChart Class (short-living)
# ----------------------------------------------------------------------
class FormatChart:
    """ 
    (short-living) Class for preparing all charts.
    """
    def __init__(self, 
                 strategies_obj : StrategyManager,
                 get_hist_table: callable,
                 get_trade_table: callable,
                 get_fng_history: callable
                 ):     
        """ 
        Args:
            strategies_obj(StrategyManager):
                object of StrategyManager /settings
            get_hist_table(callable(pair, interval)):
                get kLine historical data of pair and interval from MarketHistoryManager /market_history
            get_trade_table(callable(strategy_id)):
                get trades table from TradeManager /strategy/trades
            get_fng_history(callable()):
                get history of Fear and Gread /market_history
        """
        self._get_hist_table: callable = get_hist_table
        self._get_trade_table: callable = get_trade_table
        self._get_fng_history: callable = get_fng_history
        self._strategies_obj : StrategyManager = strategies_obj
        self._strategy: StrategyConfig = None
        self._pair:str = ""
        self._unique_intervals: list = []
        #threading
        self._lock = threading.RLock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)
    
    # Public 
    # ==================================================================  
    def get_all(self, strategy_id) -> Tuple[list[dict], dict, list[dict], list[dict],list[dict]]:
        """
        Args:
            strategy_id(Any):
                Strategy ID.
        Returns:
            Tuple[list[dict], dict, list[dict], list[dict],list[dict]]:
                Order: avgs, trades, candles,  solo_ind, inegrated_ind
        """
        try:
            with self._lock:
                self._load_vars(strategy_id)
                avgs = self._avgs()
                trades = self._trades()
                solo_ind, inegrated_ind = self._indicators()
                candles = self._candles()

            return avgs, trades, candles,  solo_ind, inegrated_ind
        except Exception as e:
            self._logger.error(f"get_all() error: {e}")
    
    # Helpers
    # ==================================================================
    # Load local data
    # ------------------------------------------------------------------    
    def _load_vars(self, strategy_id):
            strat = self._strategies_obj.get_by_id(strategy_id)
            self._strategy = strat
            self._pair = f"{strat.symbol1}{strat.symbol2}"

        
    # format Trades
    # ------------------------------------------------------------------
    def _trades(self):
        try:
            idx = self._strategy.idx
            trades = self._get_trade_table(idx)
            if trades:
                data = self._format_trades(trades)
            else:        
                data = [{
                    "x": int(self._now_ms()),
                    "y": float(0),
                    "side": "buy"
                }]
            return self._format_final(0, f"Trades" , "all", "trades", data)
        
        except Exception as e:
            self._logger.error(f"_trades() error: {e}")
    
    
    # format indicators resaults and create unique interval list
    # ------------------------------------------------------------------ 
    def _indicators(self):
        try:
            idx = self._strategy.idx
            indicators_obj = IndicatorChart(
                strategies_obj=self._strategies_obj,
                get_hist_table=self._get_hist_table,
                get_fng_hist=self._get_fng_history
            )
            solo = indicators_obj.get_solo_ind_list(idx)
            inegrated = indicators_obj.get_integrated_indc(idx)

            set_intervals= [self._strategy.candle_interval]

            solo_f = []
            if solo:
                for ind in solo:
                    set_intervals.append(ind.interval)
                    solo_f.append(self._format_final(idx, f"{ind.i_type} {ind.in1}" , ind.interval, ind.i_type, ind.val1))

            inegrated_f = []
            if inegrated:
                for idx, ind in enumerate(inegrated):
                    set_intervals.append(ind.interval)
                    if ind.i_type == "BB":
                        inegrated_f.append(self._format_final(idx, f"{ind.i_type} upper {ind.in1}" , ind.interval, ind.i_type, ind.val1))
                        inegrated_f.append(self._format_final(idx, f"{ind.i_type} middle {ind.in1}" , ind.interval, ind.i_type, ind.val2))
                        inegrated_f.append(self._format_final(idx, f"{ind.i_type} lower {ind.in1}" , ind.interval, ind.i_type, ind.val3))
                    else:
                        inegrated_f.append(self._format_final(idx, f"{ind.i_type} {ind.in1}" , ind.interval, ind.i_type, ind.val1))

            unique_intervals = set(set_intervals)
            #Sort by smaller to biggest
            self._unique_intervals = [x for x in INDICATOR_INTERVAL_LIST if x in unique_intervals]
            return solo_f, inegrated_f
        
        except Exception as e:
            self._logger.error(f"_indicators() error: {e}")

    def _candles(self):
        try:
            candles_list = []
            for idx, interval in enumerate(self._unique_intervals):
                data = self._get_hist_table(self._pair, interval)
                chart_data = self._format_candles(data)
                candles_list.append(self._format_final(idx, f"Price" , interval, "candle", chart_data))

            return candles_list
        except Exception as e:
            self._logger.error(f"_candles() error: {e}")

    def _avgs(self):
        try:
            idx = self._strategy.idx 
            avgs = []
            trade_analyzer_obj = TradeAnalyzer(get_trade_table=self._get_trade_table,
                                        get_hist_table=self._get_hist_table,
                                        get_by_id=self._strategies_obj.get_by_id
                                        )
            
            entry_list, cost_list, exit_list = trade_analyzer_obj.get_all_avgs_list(idx)
            trades = self._get_trade_table(idx)
            if not trades:
                return self._format_empty_avg(self._now_ms()), self._format_empty_avg(self._now_ms()), self._format_empty_avg(self._now_ms())
            
            entry = self._format_avg_entry_exit(entry_list, trades)
            avgs.append(self._format_final(1, "Average Entry", "all", "avg", entry))  

            cost = self._format_avg(cost_list, trades)
            avgs.append(self._format_final(2, "Average Cost", "all", "avg", cost))    

            exit_ = self._format_avg_entry_exit(exit_list, trades, entry=False)
            avgs.append(self._format_final(3, "Average Exit", "all", "avg", exit_))
                        
            return avgs
        
        except Exception as e:
            self._logger.error(f"_avgs() error: {e}")
    
    # Helpers==================================================================  
    # format trade data
    # ------------------------------------------------------------------ 
    @staticmethod
    def _format_final(idx, name, interval, type, data):
        result={
            "idx" : idx,
            "type" : type,
            "name" : name,
            "interval" : interval,
            "data" : data
            }
        return result
    
    # format trade data
    # ------------------------------------------------------------------ 
    @staticmethod
    def _format_trades(trades: list[Trade]):
        markers = []
        for t in trades:
            markers.append({
                "x": int(t.timestamp),
                "y": float(t.price),
                "side": "buy" if t.quantity1 > 0 else "sell"
            })
        return markers

    @staticmethod
    def _format_empty_avg(time):
        line=[{
            "x": int(time),
            "y": float(0)
        }]
        return line
    @staticmethod
    def _format_avg(avg: list[AverageSum], trades: list[Trade]):
        line = []
        for ind, a in enumerate(avg):
            line.append({
                "x": int(trades[ind].timestamp),
                "y": float(a.avg)
            })
        return line

    @staticmethod
    def _format_avg_entry_exit(avg: list[AverageSum], trades: list[Trade], entry = True):
        line = []
        ind = 0
        for t in trades:
            ind = ind if ind < len(avg) else -1 
            avg_y = avg[ind].avg
            line.append({
                "x": int(t.timestamp),
                "y": float(avg_y)
            })
            if entry:
                if t.quantity1 > 0:
                    ind +=1
            else:            
                if t.quantity1 < 0:
                    ind +=1

        return line    

    @staticmethod
    def _format_candles(data: IntervalData):
        candles = []
        for i in range(len(data.open)):
            candles.append({
                "x": int(data.time_open[i]),  
                "o": float(data.open[i]),
                "h": float(data.high[i]),
                "l": float(data.low[i]),
                "c": float(data.close[i]),
                "v": float(data.volume[i])
            })
        return candles
    
     # ------------------------------------------------------------------
    @staticmethod
    def _now_ms():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp()*1000)    