from src.utils.storage import save_json, load_json
from pathlib import Path
from fear_and_greed import FearAndGreedIndex
from .models import FearGread
import logging
from dataclasses import asdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FearAndGread:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data: FearAndGread = None
        self._load()

    # Internal loader
    # ---------------------------------------------------------
    def _load(self):
        #"""Load JSON file to memory."""
        raw = load_json(self.path)
        if raw is None:
            self.update()
            return
        #Convert to and save
        self._convert(raw)
        logger.debug(f"Loaded Fear & Gread {(self.data)} ")

    # Save to JSON
    # ---------------------------------------------------------
    def _save(self, raw_data):
        #Write JSON.          
        save_json(self.path, raw_data)
        #Convert to and save
        self._convert(raw_data)

    # Public 
    # ==================================================================
    def update(self):
        try:            
            now_seconds = self._now()
            time_new_dara = 0
            if self.data !=None:
                #Check if data is old
                time_new_dara= int(self.data.timestamp) + int(self.data.time_until_update) +60 #Write when new data will be available plus 60s            
            if now_seconds > time_new_dara:    #Get new data from server and save it
                self._fetch(now_seconds)      
                  
                logger.debug(f"FearAndGread() Data: {self.data}")
        except Exception as e:
            logger.error(f"FearAndGread() error: {e}")

    # Helpers
    # ==================================================================
    # Convert dict → FearGread
    # ------------------------------------------------------------------
    def _convert(self, raw):        
        self.data = FearGread(
            value=raw["value"],
            value_classification=raw["value_classification"],
            timestamp=raw["timestamp"],
            time_until_update=raw["time_until_update"],
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
            logger.error(f"FearAndGread() _fetch error: {e}")

    # ------------------------------------------------------------------
    @staticmethod
    def _now():        
        now_utc = datetime.now(timezone.utc)
        return int(now_utc.timestamp())    
    
