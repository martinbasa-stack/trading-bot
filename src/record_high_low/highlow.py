from src.utils.storage import save_json, load_json
from .models import HLRecord

import logging
from pathlib import Path
from dataclasses import asdict

logger = logging.getLogger(__name__)

class HighLowManager:
    def __init__(self, path: str, get_list_of_id_pair_func):        
        #:param path: path to JSON file
        #:param get_list_of_ids_func: function returning list of valid IDs
        self.path = Path(path)
        self.get_list_of_ids = get_list_of_id_pair_func
        self.data: dict[int, HLRecord] = {}

        self._load()

    # Internal loader
    # ==================================================================
    def _load(self):
        #"""Load JSON file to memory."""
        raw = load_json(self.path)
        if raw is None:
            logger.warning(f"JSON file not found at {self.path}. Creating empty store.")
            return
        # Convert list → dict using id as key
        for item in raw:
            try:
                self.data[item["id"]] = HLRecord(
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                )
            except KeyError as e:
                logger.error(f"Invalid record in {self.path}: {item} — missing {e}")
        logger.debug(f"Loaded {len(self.data)} HL records.")

    # Save to JSON
    # ==================================================================
    def save(self):
        #Convert dataclasses to dicts and write JSON.
        out = []
        for id_value, rec in self.data.items():
            out.append({
                "id": id_value,
                **asdict(rec)
            })
        save_json(self.path, out)

    # Public 
    # ==================================================================
    # Update high/low/close
    # ---------------------------------------------------------
    def update(self, id_value: int, close: float):
        #Creates new HLRecord if entry does not exist.
        if id_value not in self.data:
            logger.debug(f"Creating new HLRecord for ID={id_value}")
            self.data[id_value] = HLRecord.from_close(close)
            return        
        #Updates high/low/close for the given ID.
        rec = self.data[id_value]
        rec.close = close
        rec.high = max(rec.high, close)
        rec.low = min(rec.low, close)

    # Reset an ID's values
    # ---------------------------------------------------------
    def reset(self, id_value: int, reset_value: float):
        #Reset high/low/close for an ID to a specific value.
        #Creates new HLRecord if absent.        
        self.data[id_value] = HLRecord.from_close(reset_value)

    # Return record
    # ---------------------------------------------------------
    def get(self, id_value: int) -> HLRecord:
        #Returns (high, low) for the ID.
        #If ID does not exist → (None, None)
        rec = self.data.get(id_value)
        if rec is None:
            return None
        return rec

    # Cleanup removed IDs
    # ---------------------------------------------------------
    def cleanup(self):
        #Remove IDs not in get_list_of_ids().
        valid = set(self.get_list_of_ids())
        existing = set(self.data.keys())

        remove_ids = existing - valid

        for rid in remove_ids:
            logger.debug(f"Removing obsolete ID={rid}")
            self.data.pop(rid, None)

    