import requests
from datetime import datetime, timezone
import threading
import logging

from .constants import BASE_ST_URL

class SolanaTracker:     
    """ Clas for REST api connection to Solana Tracker """
    def __init__(self,
                    api: str
                    ):     
        """ Args:
            api(str): 
                API string from Solana Tracker
        """
        self.api = api
        #threading
        self._lock = threading.Lock()
        # self._logger
        # ----------------------------------------------------------------------
        self._logger = logging.getLogger("solana").getChild(self.__class__.__name__)

    def fetch_kline(self,mint_s, interval: str, num_data:int = 100) -> list[dict]: 
        """ 
        Args:
            mint_s(str): 
                SLP token mint address
            interval(str): 
                Candle interval. Options("1h", "4h", "1d", "1w",...)
            num_data(int): 
                Number of candles from now.
        Returns:
            list[dict]
                A list of OCLVH candle data:
                    {
                    "open": 253.11579943883646,
                    "close": 255.05193096987722,
                    "low": 253.11579943883646,
                    "high": 255.05193096987722,
                    "volume": 123989,
                    "time": 1756008000 # open time
                    },...
        """
        try:
            with self._lock:
                interval_s = self._interval_to_s(interval)
                url = f"{BASE_ST_URL}/chart/{mint_s}"
                time_to = self._now()
                time_from = time_to - (interval_s * (num_data + 1))
                params = {
                    "removeOutliers" : True,
                    "dynamicPools" : True,
                    "type" : interval,
                    "time_to" : time_to,
                    "time_from": time_from,
                    "timezone" : "UTC"
                }
                header = {
                    "x-api-key" :  self.api
                }

                resp = requests.get(url, params=params, headers=header)

                if resp.status_code == 200:
                    return resp["oclhv"]
                else:
                    raise ConnectionError(f"Status code: {resp.status_code}")

                
        except Exception as e:
            self._logger.error(f"fetch_kline() error: {e}")
            return False

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
                return n * 30 * 7 * 24 * 60 * 60
             
    @staticmethod         
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())   
        
