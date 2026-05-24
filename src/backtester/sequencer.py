from src.market_history import IntervalData
from src.settings import StrategyConfig

from .models import SaveCandle, Trackers

import copy
import threading
import logging 
from datetime import datetime, timezone
from typing import Dict

import numpy as np

class Sequencer:    
    """ 
    (short-living) computing strategy data from other objects
    """
    def __init__(self, 
                 get_hist_table: callable,
                 strategy : StrategyConfig,
                 get_fng_timestamp : callable,
                 balance_s1 : float,
                 balance_s2 : float
                 ):     
        """ Args:
            get_pairs_intervals(callable()): 
                get all pairs and their intervals from StrategyManager /settings
            strategy(StrategyConfig): 
                Strategy of the backtester
            get_fng_timestamp(callable(int)): 
                get fear and gread by timestamp
            balance_s1(float): 
                Available balance for symbol1
            balance_s2(float): 
                Available balance for symbol2
        """
        self._get_hist_table : callable = get_hist_table
        self._get_fng_timestamp : callable = get_fng_timestamp
        self._data: Dict[str, IntervalData] = {}  # Pair -> PairHistory
        self._data_active: Dict[str, IntervalData] = {}  # Pair -> PairHistory

        self._strategy : StrategyConfig = strategy
        self._starting_step : int = 0
        self._active_step : int = 0
        self._end_step : int = 0
        self._close_price : float = 0.0  
        self._balance_s1 : float = balance_s1
        self._balance_s2 : float = balance_s2
        self._save_candles : SaveCandle = None
        self._trackers : Trackers = Trackers()
        #At initialisation load all data 
        #threading
        self._lock = threading.Lock()
        
        self._load_all()
        
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)
    
    # Public 
    # ==================================================================
    # RUN function to be called for sequencer run
    # ------------------------------------------------------------------
    def run(self) -> bool:
        """
        Run sequencer
        
        Returns:
            bool:
                True at end
        """
        try:
            with self._lock:
                
                if self._active_step > self._end_step:
                    self._active_step = self._end_step
                    return True

                if self._strategy.candle_close_only:
                    self._active_step += 1
                    self._load_active_table()
                else:
                    self._intra_candle_step()
                    tr = self._trackers
                    if tr.to_colse_done and tr.to_high_done and tr.to_low_done:
                        self._active_step += 1
                        self._load_active_table()
                               
            return False
            
        except Exception as e:         
            self._logger.error(f"run() error: {e}")
    
    # Get data table by pair and interval imitating market history manager
    # ------------------------------------------------------------------
    def get_table(self, pair, interval) -> IntervalData:
        """
        Args:
            pair(str): Not used in backtester
            interval(str): Interva as "30m", "1d", "1w"
        Returns:
            IntervalData:
                Whole table colums are as numpy arrays
        """      
        try:  
            with self._lock:
                if not self._data_active[interval]:
                    return None
                return self._data_active[interval]
        
        except Exception as e:         
            self._logger.error(f"get_table() error: {e}")

    # Get sim now time
    # ------------------------------------------------------------------
    def get_now_sim(self) -> int:
        """
        Returns:
            timestamp:
                Simulation time
        """      
        try:  
            with self._lock:
                if not self._data_active[self._strategy.candle_interval]:
                    return None
                time_open = self._data_active[self._strategy.candle_interval].time_open[-1]
                #time_close = self._data_active[self.strategy.candle_interval].time_close[-1]
                return int(time_open + 60)
        
        except Exception as e:         
            self._logger.error(f"get_now_sim() error: {e}")

    # Get data table by pair and interval imitating market history manager
    # ------------------------------------------------------------------
    def get_close(self, pair) -> float:
        """
        Args:
            pair(str): Not used in backtester
        Returns:
            float:
                Last price
        """      
        with self._lock:
            return self._close_price
        
    # get  Fear and gread
    def get_fng_sim(self):
        try:
            interval_s = self._strategy.candle_interval
            timestamp = (self._data_active[interval_s].time_open[-1] / 1000) + 60  
            fng = self._get_fng_timestamp(int(timestamp)) 
            return fng.value
        except Exception as e:
            print(f"get_fng_sim Error : {e}")
            return 50
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
                if symbol == self._strategy.symbol1:
                    return self._balance_s1
                else:
                    return self._balance_s2
    
        except Exception as e: 
            self._logger.error(f"get_available() error: {e}")
    
    def update_balance(self, balance_s1_change, balance_s2_change):     
        """        
        Args:
            balance_s1_change(float): 
                Amount of balance added/removed after trade
            balance_s2_change(float): 
                Amount of balance added/removed after trade
        """   
        with self._lock:
            self._balance_s1 += balance_s1_change
            self._balance_s2 += balance_s2_change


    # Fill all instance data needed
    # ------------------------------------------------------------------
    def _load_all(self):
        with self._lock:
            s = self._strategy
            self._starting_step = s.lookback #Basic start
            pair = f"{s.symbol1}{s.symbol2}"
            intervals = self._generate_intervals()

            for interval in intervals:
                data = self._get_hist_table(pair, interval)
                self._data[interval] = copy.deepcopy(data)

            self._active_step = self._starting_step
            self._end_step = len(self._data[s.candle_interval].close) -1
            self._load_active_table()

    # Fill active table
    # ------------------------------------------------------------------
    def _load_active_table(self):
        s_interval = self._strategy.candle_interval
        self._data_active[s_interval] = self._truncate_intervals(self._data[s_interval], self._active_step)
        time_s_open = self._data_active[s_interval].time_open[-1]        
        time_s_close = self._data_active[s_interval].time_close[-1]    
        self._save_candles = SaveCandle(
                high=self._data_active[s_interval].high[-1],
                low=self._data_active[s_interval].low[-1],
                close=self._data_active[s_interval].close[-1]
            )        
        self._update_saved(s_interval)

        self._close_price = self._data_active[s_interval].close[-1]
        self._trackers = Trackers()     

        self._load_sub_active_tables(time_s_close)

    def _load_sub_active_tables(self, time_sim):
        s_interval = self._strategy.candle_interval 

        for interval in self._data:            
            if interval != s_interval:
                if interval in self._data_active:
                    t_close = self._data_active[interval].time_close[-1]
                    #print(f"TEST Open candle interval {s_interval} open = {datetime.fromtimestamp(int(time_s_open/1000))} | close = {datetime.fromtimestamp(int(time_s_close/1000))}")                   
                    if time_sim <= t_close:
                        continue # Do not search if interval is bigger than the main and it has not finnished
                np_idx = np.searchsorted(self._data[interval].time_close, time_sim)
                self._data_active[interval] = self._truncate_intervals(self._data[interval], np_idx+1) 
                
                time_open = self._data_active[interval].time_open[-1]
                time_close = self._data_active[interval].time_close[-1]
                #print(f"TEST Open candle interval {interval} open = {datetime.fromtimestamp(int(time_open/1000))} | close = {datetime.fromtimestamp(int(time_close/1000))}")                   
                          

            

    # Update saved candle values 
    # ------------------------------------------------------------------
    def _update_saved(self, interval):
        if not self._strategy.candle_close_only:
            self._data_active[interval].high[-1]=self._data_active[interval].open[-1]
            self._data_active[interval].low[-1]=self._data_active[interval].open[-1]
            self._data_active[interval].close[-1]=self._data_active[interval].open[-1]


    # Intra candle steps
    # ------------------------------------------------------------------
    def _intra_candle_step(self):
        s = self._strategy
        pump = (s.asset_manager.pump_sell / 100.0)
        dip = (s.asset_manager.dip_buy / 100.0)
        interval_s = s.candle_interval

        tracker = self._trackers
        saved = self._save_candles
        open_p = self._data_active[interval_s].open[-1]
        close_p = self._close_price

        if (saved.close >= open_p or tracker.to_high_done) and not tracker.to_low_done:
            tracker.go_to_low = True

        if (saved.close < open_p or tracker.to_low_done) and not tracker.to_high_done:
            tracker.go_to_high = True

        if tracker.to_high_done and tracker.to_low_done:
            tracker.go_to_colse = True
        
        # Goining to low of the candle
        if tracker.go_to_low:
            close_p = close_p * (0.9999 - dip)
            if close_p < saved.low:
                tracker.go_to_low = False
                tracker.to_low_done  = True
                close_p = saved.low

        # Goining to high of the candle
        if tracker.go_to_high:
            close_p = close_p * (1.0001 + pump)
            if close_p > saved.high:
                tracker.go_to_high = False
                tracker.to_high_done  = True
                close_p = saved.high

        # Goining to close of the candle
        if tracker.go_to_colse:
            if saved.close > open_p: # Going down from high                
                close_p = close_p * (0.9999 - dip)
                if close_p < saved.close:
                    tracker.go_to_colse = False
                    tracker.to_colse_done  = True
                    close_p = saved.close
            else: #Going up froom lows
                close_p = close_p * (1.0001 + pump)    
                if close_p > saved.close:                    
                    tracker.go_to_colse = False
                    tracker.to_colse_done  = True
                    close_p = saved.close

        self._close_price = close_p
        self._trackers = tracker     

        self._update_last_candles()

                    
    def _update_last_candles(self):
        # Update last candles 
        for interval in self._data:      
            self._data_active[interval].low[-1] = min(self._close_price, self._data_active[interval].low[-1])
            self._data_active[interval].close[-1] = self._close_price
            self._data_active[interval].high[-1] = max(self._close_price, self._data_active[interval].high[-1])

    # Function to create a list of all unique intervals
    # ------------------------------------------------------------------
    def _generate_intervals(self) ->  dict[str, dict[str, object]]:
        """        
        Returns:
            list: 
                "intervals": ["5m", "1h", "1d"]

        """
        intervals = []
        s = self._strategy
        
        intervals.append(s.candle_interval)

        # DynamicBuy
        for ind in s.indicators_buy:
            if s.candle_interval == ind.interval:
                self._starting_step = max(self._starting_step, ind.value1)
            if ind.interval not in intervals:
                intervals.append(ind.interval)

        # DynamicSell
        for ind in s.indicators_sell:
            if s.candle_interval == ind.interval:
                self._starting_step = max(self._starting_step, ind.value1)
            if ind.interval not in intervals:
                intervals.append(ind.interval)

        return intervals
    
    @staticmethod        
    def _truncate_intervals(v:  IntervalData, n: int) -> IntervalData:
        return IntervalData(
            time_open = v.time_open[:n].copy(),
            time_close= v.time_close[:n].copy(),
            open       = v.open[:n].copy(),
            close      = v.close[:n].copy(),
            high       = v.high[:n].copy(),
            low        = v.low[:n].copy(),
            volume     = v.volume[:n].copy(),
            )

    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   