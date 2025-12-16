from src.utils.storage import save_json, load_json

from .storage import save_csv, load_csv
from .models import FearGread

import logging
from datetime import datetime, timezone
from pathlib import Path
import threading
import copy

from fear_and_greed import FearAndGreedIndex

# FearAndGread Class (long-living)
# ----------------------------------------------------------------------
class FearAndGread:
    """ (long-living) Class for fetching and storing Fear&Gread value from https://alternative.me/ """
    def __init__(self,  
                 path: str,
                 get_settings: callable
                 ):   
        """ 
        Args:
            path(str):
                File path of .json.
        """
        self._path = Path(path)
        self._get_settings :callable = get_settings
        self._data: FearGread = None
        self._hist_data:list[FearGread] = None        
        self._lock =  threading.Lock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("app").getChild(self.__class__.__name__)
        
        self._load_hist()
        self._load()

    # Internal loader
    # ---------------------------------------------------------
    def _load(self):
        #"""Load JSON file to memory."""
        raw = load_json(self._path)
        if raw is None:
            self._update()
            return
        #Convert to and save
        self._data =  self._convert(raw)
        self._logger.debug(f"Loaded Fear & Gread {(self._data)} ")

    # Load historical data
    # ---------------------------------------------------------
    def _load_hist(self):
        #"""Load JSON file to memory."""
        raw = load_csv()
        if raw is None:
            self._fetch_hist()
            return
        #Convert to and save
        self._hist_data = self._convert_raw_to_hist(raw)        

    # Save to JSON
    # ---------------------------------------------------------
    def _save(self, raw_data):
        #Write JSON.          
        save_json(self._path, raw_data)

    # Save to .csv
    # ---------------------------------------------------------
    def _save_hist(self):
        if self._hist_data:            
            #Convert to raw
            raw_data = self._convert_hist_to_raw(self._hist_data)
            #Write csv.          
            save_csv(raw_data)

    # Public 
    # ==================================================================
    # Get last data
    # ---------------------------------------------------------
    def get(self) -> float:
        """    
        Returns:
            float:            
        """
        try:   
            with self._lock:         
                return copy.deepcopy(self._data.value)
        except Exception as e:
            self._logger.error(f"get() error: {e}")

    # Get last data
    # ---------------------------------------------------------
    def get_full(self) -> FearGread:
        """    
        Returns:
            FearGread:            
        """
        try:   
            with self._lock:         
                return copy.deepcopy(self._data)
        except Exception as e:
            self._logger.error(f"get() error: {e}")

    # Get first data afetr selected timestamp
    # ---------------------------------------------------------
    def get_timestamp(self, timestamp: int) -> FearGread:
        """    
        Args:
            timestamp(int):
                Timestamp for which data needs to be returned
        Returns:
            FearGread:
                First after the timestamp
        """
        try: 
            with self._lock:
                if self._hist_data: 
                    data =  self._hist_data[-1]
                    for idx, d in enumerate(self._hist_data):
                        if timestamp < d.timestamp and idx > 0:
                            data  = self._hist_data[idx-1]
                            break
                    return copy.copy(data)
        except Exception as e:
            self._logger.error(f"get_timestamp() error: {e}")      
            
        # Get first data afetr selected timestamp
    # ---------------------------------------------------------
    def get_hist(self) -> list[FearGread]:
        """ 
        Returns:
            list[FearGread]:
                Ful hist data
        """
        try:   
            with self._lock:
                if self._hist_data: 
                    num = self._get_settings("numOfHisCandles")
                    hist_data = copy.copy(self._hist_data[-num:])
                    return hist_data
        except Exception as e:
            self._logger.error(f"get_hist() error: {e}")      
    # Run for data checkup
    # ---------------------------------------------------------
    def run(self):
        """
        Update the Fear and gread data, from file or fetch from API.
        Check historical data is up to date.                
        """
        with self._lock:
            self._update()
            self._update_hist()

    # Helpers
    # ==================================================================
    # Update last data if not up to date
    # ------------------------------------------------------------------
    def _update(self):
        try:           
            now_seconds = self._now()
            time_new_data = 0
            if self._data !=None:
                #Check if data is old
                time_new_data= int(self._data.timestamp) + int(self._data.time_until_update) +60 #Write when new data will be available plus 60s            
            if now_seconds > time_new_data:    #Get new data from server and save it
                self._fetch(now_seconds)  
            
        except Exception as e:
            self._logger.error(f"_update() error: {e}")
    

    # Get complete current data (value, classification, timestamp)
    # ------------------------------------------------------------------
    def _fetch(self, now_seconds):
        try:
            fng_index = FearAndGreedIndex()
            raw = fng_index.get_current_data()
            data =  self._convert(raw)

            raw["timestamp"] = now_seconds
            self._save(raw)
            #Convert to and save
            self._data =  data
            self._data.timestamp =  now_seconds

            if self._hist_data:
                self._hist_data.append(data)
        except Exception as e:
            self._logger.error(f"_fetch() error: {e}")

    # Update historical data
    # ------------------------------------------------------------------
    def _update_hist(self):
        try:           
            now_seconds = self._now()
            time_comp = 0
            if self._hist_data:
                #Check if data is old
                time_last = self._hist_data[-1].timestamp 
                time_comp = time_last + 25 * 3600

            if now_seconds > time_comp:    #Get new data from server if more than 1 day of data is missing
                self._fetch_hist()      
                
        except Exception as e:
            self._logger.error(f"_update_hist() error: {e}")

    # Get complete historical data (value, classification, timestamp)
    # ------------------------------------------------------------------
    def _fetch_hist(self):
        try:
            fng_index = FearAndGreedIndex()
            data = fng_index.get_last_n_days(days=self._get_settings("numOfHisCandles"))
            
            self._hist_data = self._convert_hist(data)

            self._save_hist()
        except Exception as e:
            self._logger.error(f"_fetch_hist() error: {e}")


    # ------------------------------------------------------------------
    # Convert dict → FearGread
    # ------------------------------------------------------------------
    @staticmethod
    def _convert(raw):        
        return FearGread(
            value=float(raw["value"]),
            value_classification=raw["value_classification"],
            timestamp=int(raw["timestamp"]),
            time_until_update=int(raw["time_until_update"]),
        )

    @staticmethod
    def _convert_hist(raw) -> list[FearGread]: 
        arr = []
        for d in raw:   
            arr.append(FearGread(
                        value=float(d["value"]),
                        value_classification=d["value_classification"],
                        timestamp=int(d["timestamp"])
                    ))
        return arr[::-1]
       
    @staticmethod
    def _convert_hist_to_raw(hist_data: list[FearGread]) -> list[list[float,str,int]]: 
        raw = []
        for row in hist_data:       
            raw.append(
                [row.value, row.value_classification, row.timestamp]
            )
        return raw
    
    @staticmethod
    def _convert_raw_to_hist(raw: list[list[float,str,int]] ) ->  list[FearGread]: 
        hist_data = []
        for row in raw:       
            hist_data.append(FearGread(
                value=float(row[0]),
                value_classification=row[1],
                timestamp=int(row[2])
            ))
        return hist_data
        
    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())    
    
