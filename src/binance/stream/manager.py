from .models import StreamKline

import threading
from datetime import datetime, timezone
from typing import Dict
import logging

# StreamData Class (long-living)
# ---------------------------------------------------------------------- 
class StreamManager:
    """ 
        (long-living) Class for storing and managin stream data.
        
    Thread-safe with a re-entrant lock.
    """  
    def __init__(self, get_pairs: callable,
                 lock: threading.Lock
                 ):    
        """ 
        Args:
            get_pairs (Callable()):
                Get all strategy pairs from StrategyManager /settings.
                
            lock(cthreading.Lock):
                Thread lock for connecting with StreamWorker.
        """
        self._get_pairs = get_pairs
        self._data : Dict[StreamKline] = {}
        #Commands
        self._disconnect: bool = False
        self._connected: bool = False
        #threading
        self._lock = threading.RLock()
        self._comm_lock = lock

        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("binance").getChild(self.__class__.__name__)

    # Public 
    # ==================================================================
    # Write values to data 
    # ---------------------------------------------------------
    def set(self, pair, kline: StreamKline): 
        """         
        Write data.

        Args:
            pair(str):
                String of trading pair.        
            kline(StreamKline):
                Data in class data structiure.
        """
        try:
            with self._lock:
                self._data[pair] = kline
        except Exception as e:
            self._logger.error(f"set() error: {e}")
    
    # Clean up unused and get all times find the oldest
    # ---------------------------------------------------------
    def oldest(self) -> int: #Return how long ago data was recived
        """
        Return time in seconds of the oldest data stored.

        Returns:
            int:
                Time of oldest in seconds.
        """
        try:
            with self._lock:
                self._cleanup()
                now_ms = self._now_ms()
                time_list = []
                for _, kline in self._data.items():
                    time_old = now_ms - kline.time_ms
                    time_list.append(time_old)
                if not time_list:
                    return 0
                oldes_s = int(max(time_list)/1000)
                return oldes_s
        except Exception as e:
            self._logger.error(f"oldest() error: {e}")
        
        # Clean up unused and get all times find the oldest
    # ---------------------------------------------------------
    def oldest_timestamp(self) -> int: #Return timestamp of the oldest data
        """
        Return timestamp in seconds of the oldest data stored.

        Returns:
            int:
                Timestamp of oldest in s.
        """
        try:
            with self._lock:
                self._cleanup()
                time_list = []
                for _, kline in self._data.items():
                    time_list.append(kline.time_ms)
                if not time_list:
                    return int(self._now_ms()/1000)
                oldes_s = int(min(time_list)/1000)
                return oldes_s
        except Exception as e:
            self._logger.error(f"oldest_timestamp() error: {e}")
    
    # Check if all necesary stream data is available
    # ---------------------------------------------------------
    def all_streams_available(self) -> bool: 
        """
        Check if all necesary streams are available.

        Returns:
            bool: 
                Result.
        """     
        try:  
            with self._lock:
                pair_list = list(self._get_pairs().keys())
                for pair in pair_list:
                    if not pair in self._data:
                        return False
                return True
        except Exception as e:
            self._logger.error(f"all_streams_available() error: {e}")
    
    # Disconnect
    # -----------------------------------------------------------------
    def disconnect(self):
        """Signal stream to disconnect."""
        with self._comm_lock:
            self._disconnect = True

    # check connection status
    # -----------------------------------------------------------------
    def is_connected(self) -> bool:
        """
        Returns:
            bool: 
                Connection status
        """        
        with self._comm_lock:
            connected = self._connected
        with self._lock:
            return connected

    # Return StreamKline if not to old if 0  only return data
    # ---------------------------------------------------------
    def get_full(self, pair:str, max_old: int = 0) -> StreamKline:
        """
        Args:
            pair(str):
                String of trading pair.        
            max_old(int, optional):
                Limit in second of data age 0 = no limit. If data is to old return None.
        
        Returns:
            StreamKline: 
                Full data structure:
                    if to old None
        """
        try:
            with self._lock:
                if pair not in self._data:
                    return None        
                if not self.data_current(pair, max_old):
                    return None
                return self._data[pair]
        except Exception as e:
            self._logger.error(f"get_full() error: {e}")
    
    # Return close price if not to old if 0  only return data
    # ---------------------------------------------------------
    def get_close(self, pair, max_old: int = 0) -> float:
        """       
        Args:
            pair(str):
                String of trading pair.        
            max_old(int, optional):
                Limit in second of data age 0 = no limit. If data is to old return None.
        
        Returns:
            float: 
                Closing price, if not to old.
        
            None: If to old.
        """        
        try:
            with self._lock:
                if not self.get_full(pair, max_old):
                    return 0
                return self.get_full(pair, max_old).close
        except Exception as e:
            self._logger.error(f"get_close() error: {e}")
    
    # Check if data is fresh need to set max tim in s
    # ---------------------------------------------------------
    def data_current(self, pair: str, max_old: int) -> bool:        
        """
        Args:
            pair(str):
                String of trading pair.        
            max_old(int):
                Limit in second of data age.
        
        Returns:
            bool: 
                True if not old.
        """
        try:
            with self._lock:
                if pair not in self._data:
                    return False
                if not self._data_current(pair, max_old):
                    return False
                return True
        except Exception as e:
            self._logger.error(f"data_current() error: {e}")
    
    # Check if all data is fresh need to set max tim in s
    # ---------------------------------------------------------
    def all_data_current(self, max_old: int) -> bool:        
        """
        Args:       
            max_old(int):
                Limit in second of data age.
        
        Returns:
            bool: 
                True if not old.
        """
        try:
            with self._lock:
                for pair in self._data:
                    if not self._data_current(pair, max_old):
                        return False
                return True
        except Exception as e:
            self._logger.error(f"all_data_current() error: {e}")
    
    # Get list of active streams
    # ---------------------------------------------------------
    def get_active_list(self) -> Dict[str, StreamManager]:
        """
        Returns:
            Dict: 
                A dict of pairs as keys and StreamData as value.
        """
        try:
            with self._lock:
                active_list= {}
                for pair, kline in self._data.items():
                    active_list[pair] = kline.interval
                return active_list
        except Exception as e:
            self._logger.error(f"get_active_list() error: {e}")
    # Helpers
    # ==================================================================
    # Cleanup removed unused pairs
    # ---------------------------------------------------------
    def _cleanup(self):
        #Remove pairs not in get_pairs().
        valid = set(self._get_pairs().keys())
        existing = set(self._data.keys())
        
        remove_ids = existing - valid

        for rid in remove_ids:
            self._data.pop(rid, None)


    # Calculate data current
    # ---------------------------------------------------------
    def _data_current(self, pair, max_old) -> bool:
        now_ms = self._now_ms()             
        max_old = max_old *1000
        time_old = now_ms - self._data[pair].time_ms
        if max_old > 0 and max_old < time_old:
            return False
        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _now_ms():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp()*1000)    
    
