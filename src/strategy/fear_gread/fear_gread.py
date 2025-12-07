from src.utils.storage import save_json, load_json
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
    def __init__(self,  path: str):   
        """ 
        Args:
            path(str):
                File path of .json.
        """
        self.path = Path(path)
        self._data: FearGread = None
        self._lock =  threading.Lock()
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)
        
        self._load()

    # Internal loader
    # ---------------------------------------------------------
    def _load(self):
        #"""Load JSON file to memory."""
        raw = load_json(self.path)
        if raw is None:
            self._update()
            return
        #Convert to and save
        self._convert(raw)
        self._logger.debug(f"Loaded Fear & Gread {(self._data)} ")

    # Save to JSON
    # ---------------------------------------------------------
    def _save(self, raw_data):
        #Write JSON.          
        save_json(self.path, raw_data)
        #Convert to and save
        self._convert(raw_data)

    # Public 
    # ==================================================================
    def get(self) -> FearGread:
        """
        Update the Fear and gread data, from file or fetch from API    
        Returns:
            FearGread:            
        """
        try:   
            with self._lock:         
                return copy.deepcopy(self._data)
        except Exception as e:
            self._logger.error(f"get() error: {e}")


    # Helpers
    # ==================================================================
    # Convert dict → FearGread
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
                
                self._logger.debug(f"_update() Data: {self._data}")
        except Exception as e:
            self._logger.error(f"_update() error: {e}")


    def _convert(self, raw):        
        self._data = FearGread(
            value=float(raw["value"]),
            value_classification=raw["value_classification"],
            timestamp=int(raw["timestamp"]),
            time_until_update=int(raw["time_until_update"]),
        )

    #Get complete current data (value, classification, timestamp)
    # ------------------------------------------------------------------
    def _fetch(self, now_seconds):
        try:
            fng_index = FearAndGreedIndex()
            data = fng_index.get_current_data()
            data["timestamp"] = now_seconds
            self._save(data)
        except Exception as e:
            self._logger.error(f"_fetch() _fetch error: {e}")

    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())    
    
