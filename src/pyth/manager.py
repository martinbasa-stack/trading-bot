import requests
from requests import Response
from datetime import datetime, timezone
import threading
import logging
import copy


from .models import Feed, StreamData
from .stream import PythStream
from .constants import CONFIG_URL, HIST_KLINE_URL, PRICE_FEED_ID_URL, PRICE_LAST_URL

import numpy as np

class PythDataManager:     
    """ Clas for REST api connection to Solana Tracker """
    def __init__(self,
                 get_pairs: callable,
                 logger_name:str = "pyth"
                    ):     
        """ Args:                        
            get_pairs(callable(filter_only = None, filter_exclude = None)): 
                Function to retrive pairs from Strategymanager.
        """
        self._get_pairs: callable = get_pairs
        self._supported_resolutions = []
        # Stream data   
        self._data : dict[str,StreamData] = {}
        self._feed_ids: dict[str, str] = {}
        self._requested_pairs: dict[str, str] = {}
        # Data monitoring        
        self.count_no_data: int = 0
        self._max_no_data : int = 5
        self._time_old_data : int = 40 #in seconds
        self._data_error_time_reduction: int = 0
        self._data_error = False
        #threading
        self._lock = threading.RLock()
        #Stream
        self._stream = PythStream(logger_name=logger_name)
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger(logger_name).getChild(self.__class__.__name__)

        # Init
        self._config()
        self._stream.start()

    def __exit__(self, exc_type, exc, tb):
        self._stream.shutdown()

    # check connection status
    # -----------------------------------------------------------------
    def is_connected(self) -> bool:
        """
        Returns:
            bool: 
                Connection status
        """        
        connected = self._stream.is_connected()
        with self._lock:
            return connected
        
    # Disconnect
    # -----------------------------------------------------------------
    def disconnect(self):
        """Signal stream to disconnect and shutdown."""
        with self._lock:
            self._requested_pairs.clear()
            self._unsubscribe()
        self._stream.shutdown()

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
                pair = str.upper(pair)
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
                    pair_u = pair.upper()
                    if not self._data_current(pair_u, max_old):
                        return False
                return True
        except Exception as e:
            self._logger.error(f"all_data_current() error: {e}")

    # Get list of active streams
    # ---------------------------------------------------------
    def get_active_list(self) -> dict[str, str]:
        """
        Returns:
            Dict: 
                A dict of pairs as keys and feed_id as value.
        """
        try:
            with self._lock:
                active_list= {}
                for pair, data in self._data.items():
                    active_list[pair] = data.feed_id
                return active_list
        except Exception as e:
            self._logger.error(f"get_active_list() error: {e}")

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
                self._cleanup()
                pair_list = list(self._requested_pairs.keys())
                for pair in pair_list:
                    pair = str.upper(pair)
                    if not pair in self._data:
                        return False
                    if pair in self._data:
                        if self._data[pair].close == 0:
                            return False
                return True
        except Exception as e:
            self._logger.error(f"all_streams_available() error: {e}")

    # Return timestamp of the oldest data
    # ---------------------------------------------------------
    def oldest_timestamp(self) -> int:
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
                for _, data in self._data.items():
                    time_list.append(data.time_ms)
                if not time_list:
                    return int(self._now_ms()/1000)
                oldes_s = int(min(time_list)/1000)
                return oldes_s
        except Exception as e:
            self._logger.error(f"oldest_timestamp() error: {e}")


    # Get candlestick data from server
    # ---------------------------------------------------------
    def fetch_kline(self,s1, s2, interval: str, num_data:int = 100) -> list[list]: 
        """ 
        Args:
            s1(str):
                Symbol ot token 1
            s2(str):
                Symbol ot token 2
            interval(str):
                Candle interval. Options("1h", "4h", "1d", "1w",...)
            num_data(int):
                Number of candles from now.
                    Default 100 if None  is passed.
        Returns:
            list[list]
                A 2D numpy array ready for saving to hist manager and .csv:
                    [[
                    t_open, o, h, l, c, v, t_close
                    ],...]
        """
        try:
            with self._lock:
                s1_u = str.upper(s1)
                s2_u = str.upper(s2)
                if "USD" in s2_u:
                    s2_u = "USD"
                interval_s = self._interval_to_s(interval)
                resolution =  self._interval_to_resolution(interval)

                if str(resolution) not in self._supported_resolutions:
                    raise ValueError(f"Unsupported interval: {interval} / supported [min]: {self._supported_resolutions}")

                url = f"{HIST_KLINE_URL}"

                time_to = self._now()
                delta = (interval_s * (num_data))
                year = 3600 * 24 * 364
                delta = min(year, delta) # Max posible history is 1 year
                time_from = time_to - delta
                params = {
                    "symbol" : f"Crypto.{s1_u}/{s2_u}",
                    "resolution" : resolution,
                    "to" : time_to,
                    "from": time_from
                }

                resp = requests.get(url, params=params)
                resp_js = self._response_json(resp)
                if "t" not in resp_js:
                    raise ValueError("No data in response")
                return self._pyth_to_rows(resp_js)
            
        except Exception as e:
            self._logger.error(f"fetch_kline() error: {e}")
            return None

    # Return StreamData 
    # ---------------------------------------------------------
    def get_full(self, pair:str) -> StreamData:
        """
        Args:
            pair(str):
                String of trading pair.        
        
        Returns:
            StreamKline: 
                Full data structure:
        """
        try:
            with self._lock:                
                pair = str.upper(pair)
                return self._data[pair]
            
        except Exception as e:
            self._logger.error(f"get_full() error: {e}")
    
    # Check if pair available  
    # ---------------------------------------------------------
    def is_available(self, s1:str, s2:str) -> bool:
        """
        Args:
            s1(str):
                Symbol1 of trading pair.      
            s2(str):
                Symbol2 of trading pair.             
        Returns:
            bool: 
                Result
        """
        try:
            with self._lock:            
                d=  self._price_ids(s1, s2)
                if not d:
                    return False
                return True
            
        except Exception as e:
            self._logger.error(f"get_full() error: {e}")
    

    # Get price
    # ---------------------------------------------------------
    def get_close(self, pair) -> float:
        """ 
        Args:
            pair(str):
                Symbol pair 
        Returns:
            float
                If there is price it will return price in float.
        """
        with self._lock:            
            pair = str.upper(pair)
            if pair not in self._data:
                return None
            return copy.copy(self._data[pair].close)
        
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
                for _, data in self._data.items():
                    if data.close == 0:
                        continue
                    time_old = now_ms - data.time_ms
                    time_list.append(time_old)
                if not time_list:
                    return 0
                oldes_s = int(max(time_list)/1000)
                return oldes_s
            
        except Exception as e:
            self._logger.error(f"oldest() error: {e}")

    # Main loop
    # =================================================================
    def run(self):
        with self._lock:
            
            if self._data_error :
                self._stream.reconnect()
                self._data_error = False

            self._build_requested_streams()

            if not self._stream.is_connected():
                return
            
            self._subscribe()
            self._unsubscribe()
            self._cleanup()
        
            self._monitor_data_integrity()
        
    
    # Get price IDs with symbols
    # ---------------------------------------------------------
    def _price_ids(self, s1:str, s2: str = None) -> dict[str , Feed]:
        try:
            s1_u = str.upper(s1)  
            asset_type = "crypto_redemption_rate"
            if s2:
                s2_u = str.upper(s2)
                if "USD" in s2_u:
                    s2_u = "USD"          
                    asset_type = "crypto"
                    

            url = PRICE_FEED_ID_URL
            params = {
                    "query" : s1_u,
                    "asset_type" : asset_type
                }
            resp = requests.get(url, params=params)
            resp_js = self._response_json(resp)
            ids_list={}
            for ids in resp_js:                
                attrib = ids["attributes"]
                if s2 is None:
                    pair = str.upper(f"{attrib["base"]}{attrib["quote_currency"]}")
                    ids_list[pair] =(Feed(
                        idx = ids["id"],
                        base = attrib["base"],
                        quote_currency = attrib["quote_currency"],
                        symbol_code= attrib["symbol"]
                    ))
                    continue
                if s2_u == attrib["quote_currency"] and s1_u == attrib["base"]:                    
                    pair = str.upper(f"{s1_u}{str.upper(s2)}")
                    ids_list[pair] = (Feed(
                        idx = ids["id"],
                        base = attrib["base"],
                        quote_currency = attrib["quote_currency"],
                        symbol_code= attrib["symbol"]
                    ))
                    return ids_list
                
            return ids_list
        except Exception as e:
            self._logger.error(f"_price_ids() error: {e}")
            return False
    
    # Subscription Management
    # ==================================================================
    # Subscribe
    # -----------------------------------------------------------------
    def _subscribe(self) -> list[str]:
        try:
            for pair_m, item in self._requested_pairs.items():
                pair = str.upper(pair_m)
                if pair not in self._data:
                    # Get feed data
                    d = self._price_ids(item["s1"], item["s2"])
                    f = d[pair]
                    # Prapare data
                    self._feed_ids[f.idx] = pair
                    self._data[pair]= StreamData(
                        time_ms= 0,
                        feed_id= f.idx,
                        pair= pair,
                        s1= f.base,
                        s2= f.quote_currency,
                        close= 0.0
                    )
                    # Subscribe
                    self._stream.subscribe(f.idx, self._on_stream_msg)
                    print(f"Pyth subscribe: {pair} id:{f.idx}")
                    self._logger.info(f"Pyth subscribe: {pair} id:{f.idx}")
                    

        except Exception as e:
            self._logger.error(f"_subscribe() error: {e}")

    # Unsubscribe
    # -----------------------------------------------------------------
    def _unsubscribe(self) -> list[str]:
        try:
            for pair in list(self._data.keys()):
                if pair not in self._requested_pairs:
                    # Get feed id
                    feed_id = self._data[pair].feed_id

                    self._stream.unsubscribe(feed_id)

                    # Delete data
                    self._data.pop(pair, None)
                    self._feed_ids.pop(feed_id, None)
                    print(f"Pyth unsubscribe: {pair} id:{feed_id}")
                    self._logger.info(f"Pyth unsubscribe: {pair} id:{feed_id}")
            
        except Exception as e:
            self._logger.error(f"_unsubscribe() error: {e}")
    
    # Bilda requested streams
    # -----------------------------------------------------------------
    def _build_requested_streams(self) -> list[str]:
        self._requested_pairs.clear()
        data = self._get_pairs(filter_only="DEX")
        for pair, item in data.items():
            self._requested_pairs[str.upper(pair)]= {
                "s1" : item["s1"],
                "s2" : item["s2"]
            }
            
    # Function for reciving data msg from stream
    # ---------------------------------------------------------
    def _on_stream_msg(self, update):
        try:
            price_info = update["price"]
            price = float(price_info["price"]) * 10** int(price_info["expo"])
            ts = price_info["publish_time"]
            idx = update["id"]

            with self._lock:
                if idx not in self._feed_ids:
                    return                
                pair = self._feed_ids[idx]
                if pair not in self._data:
                    return
                self._data[pair].close = price
                self._data[pair].time_ms = ts *1000
            
        except Exception as e:
            self._logger.error(f"_on_stream_msg() error: {e}")

    # Monitoring & Integrity
    # ==================================================================    
    # Check data aging
    # -----------------------------------------------------------------
    def _monitor_data_integrity(self):
        time_old_data = self._time_old_data
        time_oldest = self.oldest()
        time_compare = time_oldest - self._data_error_time_reduction
        if (
            time_compare > time_old_data
            and self.all_streams_available()
        ):
            self.count_no_data += 1
            self._data_error_time_reduction = time_oldest
            if self.count_no_data > 0:
                timestamp_oldest = self.oldest_timestamp()
                self._logger.warning(
                    f"StreamWorker no data received: {self.count_no_data} | time oldest= {time_oldest} s | timestamp of oldest stream= {datetime.fromtimestamp(int(timestamp_oldest))} s"
                )                
                print(f"Pyth Stream no data count: {self.count_no_data} | time oldest= {time_oldest} s | timestamp of oldest stream= {datetime.fromtimestamp(int(timestamp_oldest))} s")
                #self._stream.ping()
                # Unsubscribe
                #self._requested_pairs.clear()
                #self._unsubscribe()

            if self.count_no_data > self._max_no_data:
                self._logger.error(f"Pyth Stream data starvation detected!")
                print(f"Pyth Stream data starvation detected!")
                self._data_error = True
                self.count_no_data = 0
                

        if time_oldest < self._data_error_time_reduction:
            self.count_no_data = 0
            self._data_error_time_reduction = 0
            self._logger.info(f"New data recived. time oldest= {time_oldest} s")
            print("Pyth New data recived.")

    # Helpers
    # ==================================================================
    # Cleanup removed unused pairs
    # ---------------------------------------------------------
    def _cleanup(self):
        #Remove pairs not in _requested_pairs().
        valid = set(self._requested_pairs.keys())
        existing = set(self._data.keys())

        remove_ids = existing - valid
        for rid in remove_ids:
            self._data.pop(rid, None)
    # Get data from server resolution list
    # ---------------------------------------------------------
    def _config(self): 
        """ 
        Save server configs to local data
        """
        try:
            url = f"{CONFIG_URL}"

            resp = requests.get(url)
            resp_js = self._response_json(resp)

            self._supported_resolutions=  resp_js["supported_resolutions"]
            
        except Exception as e:
            self._logger.error(f"_config() error: {e}")
            return False
        
    # Calculate data current
    # ---------------------------------------------------------
    def _data_current(self, pair, max_old) -> bool:
        now_ms = self._now_ms()             
        max_old = max_old *1000
        time_old = now_ms - self._data[pair].time_ms
        if max_old > 0 and max_old < time_old:            
            self._logger.warning(f"Old data for pair: {pair} time old: {time_old/1000} s")
            return False
        return True
    
    # Utilities
    # ==================================================================
    # Format rows for .csv and DataManager
    # ---------------------------------------------------------
    @staticmethod
    def _pyth_to_rows(data: dict) -> np.ndarray:
        """
        Convert Pyth benchmark OHLCV columns into row-based array.

        Returns:
            np.ndarray shape (n, 7)
            [open_time_ms, open, high, low, close, volume, close_time_ms]
        """
        t = np.asarray(data["t"], dtype=np.int64) * 1000  # ms
        o = np.asarray(data["o"], dtype=np.float64)
        h = np.asarray(data["h"], dtype=np.float64)
        l = np.asarray(data["l"], dtype=np.float64)
        c = np.asarray(data["c"], dtype=np.float64)
        v = np.asarray(data["v"], dtype=np.float64)

        # Infer interval (robust for last candle)
        if len(t) > 1:
            interval_ms = t[1] - t[0]
        else:
            interval_ms = 60_000  # fallback (1 min)

        t_close = t + interval_ms - 1

        return np.column_stack((t, o, h, l, c, v, t_close))

    # Generate dict from response if successful
    # ---------------------------------------------------------
    @staticmethod
    def _response_json(resp: Response) -> dict:   
        if not resp.status_code == 200:
            raise ConnectionError(f"Response error status code: {resp.status_code}")
        resp_js = resp.json()    
              
        #if not resp_js["success"]:
        #    raise ConnectionError(f"Response unsuccessful id: {resp_js["id"]}")

        return resp_js

    # Transform interval to seconds
    @staticmethod
    def _interval_to_s(interval: str) -> int:
        n = int(interval[:-1])
        t = interval[-1]
        match t:
            case "m":
                return n * 60
            case "h":
                return n * 60 * 60 
            case "d":
                return n * 24 * 60 * 60 
            case "w":
                return n * 7 * 24 * 60 * 60 
            case "M":
                return n * 30 * 24 * 60 * 60
            
    # Transform interval to resolution min and h are in seconds 
    @staticmethod
    def _interval_to_resolution(interval: str) -> str:
        n = int(interval[:-1])
        t = interval[-1]
        match t:
            case "m":
                return n 
            case "h":
                return n * 60 
            case _:
                return interval.upper()
    
    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(timezone.utc).timestamp()*1000)

    @staticmethod         
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
        
