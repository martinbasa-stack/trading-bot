from src.utils.storage import save_json, load_json
from .models import HLRecord

import logging
from pathlib import Path
from dataclasses import asdict
import threading
import copy

# HighLowManager Class (long-living)
# ----------------------------------------------------------------------
class HLRecordManager:
    """ (long-living) Class for managing and storing records of high and low price values after trade. """
    def __init__(self, path: str, get_list_of_id_pair: callable):    
        """ 
        Args:
            path(str):
                File path of te .json.
            get_list_of_id_pair(callable()):
                get list of id_pair form from StrategyManager /settings
        """    
        #:param path: path to JSON file
        #:param get_list_of_ids_func: function returning list of valid IDs
        self._path = Path(path)
        self._get_list_of_ids = get_list_of_id_pair
        self._data: dict[int, HLRecord] = {}
        self._lock =  threading.Lock()
        
        # --- Logger Setup ---
        self._logger = logging.getLogger("strategy").getChild(self.__class__.__name__)

        self._load()


    # Internal loader
    # ==================================================================
    def _load(self):
        #"""Load JSON file to memory."""
        raw = load_json(self._path)
        if raw is None:
            self._logger.warning(f"JSON file not found at {self._path}. Creating empty store.")
            return
        # Convert list → dict using id as key
        for item in raw:
            try:
                self._data[item["id"]] = HLRecord(
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                )
            except KeyError as e:
                self._logger.error(f"Invalid record in {self._path}: {item} — missing {e}")
        self._logger.debug(f"Loaded {len(self._data)} HL records.")

    # Save to JSON
    # ==================================================================
    def save(self):
        """ Save local data to .json file"""
        #Convert dataclasses to dicts and write JSON.
        out = []
    
        with self._lock:
            for id_pair, rec in self._data.items():
                out.append({
                    "id": id_pair,
                    **asdict(rec)
                })
            save_json(self._path, out)

    # Public 
    # ==================================================================
    # Update high/low/close
    # ---------------------------------------------------------
    def update(self, id_pair: str, close: float):
        """
        Writes close value to low/heigh if below/above.
        Args:
            id_pair(str):
                Strategy ID and its pair as ID_pair.
            close(float):
                New close price.
        """
        #Creates new HLRecord if entry does not exist.
        with self._lock:
            if id_pair not in self._data:
                self._logger.debug(f"Creating new HLRecord for ID={id_pair}")
                self._data[id_pair] = HLRecord.from_close(close)
                return        
            #Updates high/low/close for the given ID.
            rec = self._data[id_pair]
            rec.close = close
            rec.high = max(rec.high, close)
            rec.low = min(rec.low, close)

    # Reset an ID's values
    # ---------------------------------------------------------
    def reset(self, id_pair: str, reset_value: float):
        """
        Writes reset_value value to close, low and heigh. Resets low and heigh tracking
        Args:
            id_pair(str):
                Strategy ID and its pair as ID_pair.
            reset_value(float):
                A value to set all other values to.
        """
        #Reset high/low/close for an ID to a specific value.
        #Creates new HLRecord if absent.        
        with self._lock:
            self._data[id_pair] = HLRecord.from_close(reset_value)

    # Return record
    # ---------------------------------------------------------
    def get(self, id_pair: str) -> HLRecord:
        """        
        Args:
            id_pair(str):
                Strategy ID and its pair as ID_pair.
        Returns:
            HLRecord:
                Record data of ID_pair.        
        """
        #Returns (high, low) for the ID.
        #If ID does not exist → (None, None)        
        with self._lock:
            rec = copy.deepcopy(self._data.get(id_pair))
            if rec is None:
                return None
            return rec

    # Cleanup removed IDs
    # ---------------------------------------------------------
    def cleanup(self):
        """ Removes unused values when strategy settings change..."""
        #Remove IDs not in get_list_of_ids().        
        with self._lock:
            valid = set(self._get_list_of_ids())
            existing = set(self._data.keys())

            remove_ids = existing - valid

            for rid in remove_ids:
                self._logger.debug(f"Removing obsolete ID={rid}")
                self._data.pop(rid, None)

    