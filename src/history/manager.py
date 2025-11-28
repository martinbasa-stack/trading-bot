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

import numpy as np

class HistoryManager:
    def __init__(self, get_pairs_intervals_func):
        # get_pairs_intervals is a function get_pairs_intervals() from another class
        self.get_pairs_intervals = get_pairs_intervals_func
        self.data: Dict[int, PairHistory] = {}  # Pair -> PairHistory
        self.last_update : int = self._now() #Set last update time
        #At initialisation load all data 
        self._load_all()
    
    # Public 
    # ==================================================================
    # RUN function to be called repeatedly to maintain data consistency
    def run(self, update_hist_min: int) -> bool:
        now_seconds = self._now()
        
        self._cleanup()

        if not self._is_up_to_date():
            self.last_update = now_seconds
            return True #Returns true if new data is neaded
        
        if self._missing_files():
            self.last_update = now_seconds
            return True #Returns true if new data is neaded

        since_update = now_seconds - self.last_update
        if since_update > (update_hist_min *60):
            self.last_update = now_seconds
            return True #Returns true if new data is neaded

        return False
    #Update when new data is recived
    # ------------------------------------------------------------------
    def update_interval(self, s1, s2, interval, rows): #s1 Symbol; rows -> New data recived
        pair = f"{s1}{s2}" 
        if not pair in self.data: #Create if it does not exists
            self.data[pair] = PairHistory(s1,s2,{})
        #Save data localy
        arr = np.array(rows, dtype=np.float64) 
        self.data[pair].intervals[interval] = self._array_to_interval(arr)
        #Save data to file
        path = build_candle_path(s1, s2, interval)
        save_csv(path, rows)

    #Update last candle of histordata from stream
    # ------------------------------------------------------------------
    def update_last(self, pair, new_close):
        hist = self.data[pair]
        for _, d in hist.intervals.items(): #go trough different intervals 
            d.close[-1] = new_close
            d.high[-1] = max(d.high[-1], new_close)
            d.low[-1] = min(d.low[-1], new_close)  

    # Helpers
    # ==================================================================
    # load all history only execute on start
    # ------------------------------------------------------------------
    def _load_all(self):
        pair_intervals = self.get_pairs_intervals()

        for pair, info in pair_intervals.items(): #run trough all pairs
            #Creat a dicionary structure for each pair and candle interval
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            self.data[pair] = PairHistory(
                symbol1=s1,
                symbol2=s2,
                intervals={}
            )
            for interval in info["Intervals"]: # run trough all intervals
                path = build_candle_path(s1,s2,interval)  
                arr = load_csv(path) #load data   
                if arr is None:#If no data
                    continue
                self.data[pair].intervals[interval] = self._array_to_interval(arr)

    #Check candles hist data aging
    # ------------------------------------------------------------------
    def _is_up_to_date(self) -> bool:    
        now_seconds = self._now()    
        for _, hist in self.data.items():
            for _, d in hist.intervals.items():
                ts_close = int(d.time_close[-1] / 1000)
                if (ts_close < now_seconds) : #Check if now() is bigger than timestamp of close the data is old 
                    return False
        return True
        
    #History cleanup -> delete data not used in any of the stratagies (preventing accesing old data in case of reuse strategy)
    # ------------------------------------------------------------------
    def _cleanup(self):
        paths_to_keep = []
        pair_intervals = self.get_pairs_intervals()  
                
        for _, info in pair_intervals.items():
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            for interval in info["Intervals"]:
                #build all paths that should exist
                path = build_candle_path(s1,s2,interval)  
                paths_to_keep.append(path)

        delete_csv(paths_to_keep) #remove file

    # ------------------------------------------------------------------
    def _missing_files(self) -> bool:
        pairs_intervals = self.get_pairs_intervals()
        for _, info in pairs_intervals.items(): #run trough pairs
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            for interval in info["Intervals"]:  #run trough intervals
                #build path that should exist
                path = build_candle_path(s1,s2,interval) 
                if not os.path.exists(path):
                    return True                 
        return False
    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
    
    #Define data structure 
    @staticmethod
    def _array_to_interval(arr):
        return IntervalData(
            time_open  = arr[:, KLINE_TABLE_COL_TIMESTAMP_OPEN],
            time_close = arr[:, KLINE_TABLE_COL_TIMESTAMP_CLOSE],
            open       = arr[:, KLINE_TABLE_COL_OPEN],
            close      = arr[:, KLINE_TABLE_COL_CLOSE],
            high       = arr[:, KLINE_TABLE_COL_HIGH],
            low        = arr[:, KLINE_TABLE_COL_LOW],
            volume     = arr[:, KLINE_TABLE_COL_VOLUME_S1],
        )


        

