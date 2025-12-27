from .models import PairHistory, IntervalData
from .storage import load_csv, save_csv, build_candle_path, delete_csv
from src.constants import (
                         KLINE_TABLE_COL_VOLUME_S1,
                         KLINE_TABLE_COL_LOW,
                         KLINE_TABLE_COL_HIGH,
                         KLINE_TABLE_COL_CLOSE,
                         KLINE_TABLE_COL_OPEN,
                         KLINE_TABLE_COL_TIMESTAMP_CLOSE,
                         KLINE_TABLE_COL_TIMESTAMP_OPEN
                         )

import os
from datetime import datetime, timezone
from typing import Dict
import threading
import logging
import copy

import numpy as np


# MarketHistoryManager Class (long-living)
# ----------------------------------------------------------------------
class MarketHistoryManager:
    """ (long-living) Class for managing storage and updatates of Historical kLine Market data """
    def __init__(self, 
                 get_pairs_intervals: callable,
                 settings_get: callable,
                 provider : str = "Binance"
                 ):     
        """ 
        Args:
            get_pairs_intervals(callable()): 
                get all pairs and their intervals from StrategyManager /settings
            settings_get(callable()): 
                get settings from SettingsManager /settings
        """
        self._get_pairs_intervals : callable = get_pairs_intervals
        self._settings_get : callable = settings_get
        self._provider: str = provider
        self._data: dict[str, PairHistory] = {}  # Pair -> PairHistory
        self._last_update : int = self._now() #Set last update time
        #At initialisation load all data 
        self._load_all()
        
        #threading
        self._lock = threading.Lock()
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)
    
    # Properties
    @property
    def provider(self) ->str:
        return self._provider
        
    @property
    def last_update(self) ->int:
        """ time in seconds"""
        return self._last_update
        
    # Public 
    # ==================================================================
    # RUN function to be called repeatedly to maintain data consistency
    def data_update_req(self) -> bool:
        """
        Run for data consistency check and cleanup.
        
        Returns:
            bool:
                If True data update is requred.
        """
        try:
            with self._lock:
                now_seconds = self._now()
                
                self._cleanup()

                if not self._is_up_to_date():
                    self._last_update = now_seconds
                    return True #Returns true if new data is neaded
                
                if self._missing_files():
                    self._last_update = now_seconds
                    return True #Returns true if new data is neaded
                
                update_hist_min = self._settings_get("histDataUpdate")
                since_update = now_seconds - self._last_update
                if since_update > (update_hist_min *60):
                    self._last_update = now_seconds
                    return True #Returns true if new data is neaded

                return False
            
        except Exception as e:         
            self._logger.error(f"run() error: {e}")
    # RUN function to be called repeatedly to maintain data consistency
    # ------------------------------------------------------------------
    def get_list_to_update(self) -> dict[str, dict[str, object]]:
        """        
        Returns:
        dict[str, dict[str, object]]: Dictionary in the form:
        {
            "BTCUSDT": {
                "Symbol1": "BTC",
                "Symbol2": "USDT",
                "Intervals": ["5m", "1h", "1d"]
            },
            ...
        }
        """        
        try:
            with self._lock:
                self._cleanup()

                result = self._merge_pair_intervals(
                    a= self._missing_file_list(),
                    b=self._up_to_date_list()
                )

                return result
        
        except Exception as e:         
            self._logger.error(f"get_list_to_update() error: {e}")
    
    # Update when new data is recived
    # ------------------------------------------------------------------
    def update_interval(self, s1, s2, interval, rows): #s1 Symbol; rows -> New data recived
        """
        Saves new historical data. From Binance time open and close in ms
        Args:
            s1(str): Symbol1
            s2(str): Symbol2
            interval(str): Interva as "30m", "1d", "1w"
            rows(list): New data to be saved 
        """
        try:
            with self._lock:
                pair = f"{s1}{s2}" 
                if not pair in self._data: #Create if it does not exists
                    self._data[pair] = PairHistory(s1,s2,{})
                #Save data localy
                arr = np.array(rows, dtype=np.float64) 
                self._data[pair].intervals[interval] = self._array_to_interval(arr)
                #Save data to file
                path = build_candle_path(s1, s2, interval, self._provider)
                save_csv(path, rows)

        except Exception as e:         
            self._logger.error(f"update_interval() error: {e}")

    # Update last candle of histordata from stream
    # ------------------------------------------------------------------
    def update_last(self, pair, new_close):
        """
        Updates last candle of all intervals.
        Args:
            pair(str): Symbol pair to update.
            new_close(float): New close price of the pair.
        """
        try:
            with self._lock:
                timestamp = self._now() *1000
                                
                if pair not in self._data:
                    raise RuntimeError(f"No history data for {pair}")
                
                hist = self._data[pair]
                for _, d in hist.intervals.items(): #go trough different intervals 
                    if timestamp < int(d.time_close[-1]):
                        d.close[-1] = new_close
                        d.high[-1] = max(d.high[-1], new_close)
                        d.low[-1] = min(d.low[-1], new_close)  

        except Exception as e:         
            self._logger.error(f"update_last() error: {e}")

    # Get data table by pair and interval
    # ------------------------------------------------------------------
    def get_table(self, pair, interval) -> IntervalData:
        """
        Args:
            pair(str): Symbol pair to update.
            interval(str): Interva as "30m", "1d", "1w"
        Returns:
            IntervalData:
                Whole table colums are as numpy arrays
        """      
        try:  
            with self._lock:
                if pair not in self._data:
                    raise RuntimeError(f"No history data for {pair}")
                if interval not in self._data[pair].intervals:
                    raise RuntimeError(f"No history data for {pair} of {interval}")
                
                return copy.copy(self._data[pair].intervals[interval])
        
        except Exception as e:         
            self._logger.error(f"get_table() error: {e}")
    
    # Get time_close columne by pair and interval
    # ------------------------------------------------------------------
    def get_time_close(self, pair, interval) -> list[int]:
        """
        Args:
            pair(str): Symbol pair to update.
            interval(str): Interva as "30m", "1d", "1w"
        Returns:
            list[int]:
                Return closing time colum numpy arrays
        """      
        try:  
            with self._lock:
                if not self._data[pair].intervals[interval]:
                    return None
                arr = self._data[pair].intervals[interval].time_close
                return arr.astype(int)
            
        except Exception as e:         
            self._logger.error(f"get_time_close() error: {e}")
    
    # Get time_open columne by pair and interval
    # ------------------------------------------------------------------
    def get_time_open(self, pair, interval) -> list[int]:
        """
        Args:
            pair(str): Symbol pair to update.
            interval(str): Interva as "30m", "1d", "1w"
        Returns:
            list[int]:
                Return opening time colum numpy arrays
        """      
        try:  
            with self._lock:
                if not self._data[pair].intervals[interval]:
                    return None
                arr = self._data[pair].intervals[interval].time_open
                return arr.astype(int)
        
        except Exception as e:         
            self._logger.error(f"get_time_open() error: {e}")
        
    # Helpers
    # ==================================================================
    # load all history only execute on start
    # ------------------------------------------------------------------
    def _load_all(self):
        pair_intervals : dict[str, dict[str, object]] = self._get_pairs_intervals(self._provider)

        for pair, info in pair_intervals.items(): #run trough all pairs
            #Creat a dicionary structure for each pair and candle interval
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            self._data[pair] = PairHistory(
                symbol1=s1,
                symbol2=s2,
                intervals={}
            )
            for interval in info["Intervals"]: # run trough all intervals
                path = build_candle_path(s1,s2,interval, self._provider)  
                arr = load_csv(path) #load data   
                if arr is None:#If no data
                    continue
                self._data[pair].intervals[interval] = self._array_to_interval(arr)

    # Check candles last candle is to old hist data aging
    # ------------------------------------------------------------------
    def _is_up_to_date(self) -> bool:    
        now_seconds = self._now()    
        for _, hist in self._data.items():
            for _, d in hist.intervals.items():
                ts_close = int(d.time_close[-1] / 1000)
                if (ts_close < now_seconds) : #Check if now() is bigger than timestamp of close the data is old 
                    return False
        return True
    
    # Make a list of old candles
    # ------------------------------------------------------------------
    def _up_to_date_list(self) -> dict[str, dict[str, object]]: 
        result :dict[str, dict[str, object]] = {}
        now_seconds = self._now()    
        for pair, hist in self._data.items():
            for interval, d in hist.intervals.items():
                ts_close = int(d.time_close[-1] / 1000)
                if (ts_close < now_seconds) : #Check if now() is bigger than timestamp of close the data is old 
                    if pair not in result: #If unique add
                        result[pair] = {
                            "Symbol1" : hist.symbol1,
                            "Symbol2" : hist.symbol2,
                            "Intervals" : []
                        }
                    if not interval in result[pair]["Intervals"]:#Check if unique not realy necesary
                        result[pair]["Intervals"].append(interval) #Add to the list of intervals
        return result
        
    # History cleanup -> delete data not used in any of the stratagies (preventing accesing old data in case of reuse strategy)
    # ------------------------------------------------------------------
    def _cleanup(self):
        paths_to_keep = []
        pair_intervals = self._get_pairs_intervals(self._provider)  
                
        for _, info in pair_intervals.items():
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            for interval in info["Intervals"]:
                #build all paths that should exist
                path = build_candle_path(s1,s2,interval, self._provider)  
                paths_to_keep.append(path)
        delete_csv(paths_to_keep, self._provider) #remove file

    # Any missing files
    # ------------------------------------------------------------------
    def _missing_files(self) -> bool:
        missing_list = self._missing_file_list() 
        if missing_list:
            return True
        return False
    
    # build missing file list
    # ------------------------------------------------------------------
    def _missing_file_list(self) -> dict[str, dict[str, object]]:
        result  : dict[str, dict[str, object]] ={}
        pairs_intervals : dict[str, dict[str, object]] = self._get_pairs_intervals(self._provider)
        for pair, info in pairs_intervals.items(): #run trough pairs
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            for interval in info["Intervals"]:  #run trough intervals
                #build path that should exist
                path = build_candle_path(s1,s2,interval, self._provider) 
                if not os.path.exists(path):
                    if pair not in result: #If unique add
                        result[pair] = {
                            "Symbol1" : s1,
                            "Symbol2" : s2,
                            "Intervals" : []                        
                        }
                    if interval not in result[pair]["Intervals"]:
                        result[pair]["Intervals"].append(interval)
        return result
    
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_pair_intervals(a: dict, b: dict) -> dict:
        """
        Merge two pair/interval dictionaries safely.
        """
        if not a:
            return b.copy()

        if not b:
            return a.copy()

        result = a.copy()

        for pair, info in b.items():
            if pair not in result:
                result[pair] = info.copy()
            else:
                # Merge intervals uniquely
                result[pair]["Intervals"] = list(
                    set(result[pair]["Intervals"]) |
                    set(info["Intervals"])
                )

        return result


    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
    
    # Define data structure 
    @staticmethod
    def _array_to_interval(arr) -> IntervalData:
        return IntervalData(
            time_open  = arr[:, KLINE_TABLE_COL_TIMESTAMP_OPEN].astype(np.int64),
            open       = arr[:, KLINE_TABLE_COL_OPEN],
            high       = arr[:, KLINE_TABLE_COL_HIGH],
            low        = arr[:, KLINE_TABLE_COL_LOW],
            close      = arr[:, KLINE_TABLE_COL_CLOSE],
            volume     = arr[:, KLINE_TABLE_COL_VOLUME_S1],
            time_close = arr[:, KLINE_TABLE_COL_TIMESTAMP_CLOSE].astype(np.int64),
        )
    


