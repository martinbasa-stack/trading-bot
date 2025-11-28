from src.utils.storage import save_json, load_json
from .changes import get_changes
import logging
import copy
from pathlib import Path
from typing import Dict

# StrategyManager Class
# ----------------------------------------------------------------------
class StrategyManager:
    #Manages reading, writing, updating and cloning strategy settings
    #with secure and detailed change logging.
    def __init__(self, file_path: str, log_path: str, interval_list: list):
        self.file_path = Path(file_path)
        self.log_path = Path(log_path)
        self.interval_list = interval_list
        # --- Logger Setup ---
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # prevent duplicate logs

        file_handler = logging.FileHandler(self.log_path, mode="a")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(file_handler)

        self.strategies = self._load_json()
        self._ensure_ids_unique()
    
    # Internal JSON I/O
    # ==================================================================
    def _load_json(self) -> list:
        #Load strategies from disk or initialize empty file.
        if not self.file_path.exists():
            self._save_json([])
            return []
        try:
            return load_json(self.file_path)
        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")
            return []

    def _save_json(self, data: list):
        #Write strategies to disk with safe logging.
        try:
            old = self._load_json()#copy.deepcopy(self.strategies)
            save_json(self.file_path, data)
            self._log_changes(old, data)
        except Exception as e:
            self.logger.error(f"Error saving strategies: {e}")

    # Public 
    # ==================================================================
    def get_all(self) -> list[Dict]:
        return self.strategies
    
    #Get one strategy by its ID value
    # ------------------------------------------------------------------
    def get_by_id(self, strategy_id: int) -> Dict:
        idx = self._get_index_by_id(strategy_id)
        return self.strategies[idx]
    
    # ------------------------------------------------------------------
    def save(self):
        self._save_json(self.strategies)
    
    #Write one value and save (Not for indicator changes)
    # ------------------------------------------------------------------
    def set(self, strategy_id: int, key: str, value) -> None:
        #Set a setting and save immediately
        if "Dynamic" not in key:
            idx = self._get_index_by_id(strategy_id)
            self.strategies[idx][key] = value
            self.save()
    
    #return list of all strategy ID s
    # ------------------------------------------------------------------
    def id_list(self) -> list:        
        list = []
        for s in self.strategies:
            list.append(s["id"])
        return list
    
    #Return list of pairs
    # ------------------------------------------------------------------
    def id_pair_list(self) -> list:        
        list = []        
        for s in self.strategies:
            s1 = s["Symbol1"]
            s2 = s["Symbol2"]
            list.append(f"{s["id"]}_{s1}{s2}")
        return list
 
    # Add Strategy
    # ------------------------------------------------------------------
    def add(self, data: dict) -> int:
        new_id = self._generate_new_id()
        data["id"] = new_id
        data["run"] = False #Disable automatic run
        self.strategies.append(copy.deepcopy(data))
        self.save()
        return new_id

    # Update Strategy
    # ------------------------------------------------------------------
    def update(self, strategy_id: int, data: dict):
        idx = self._get_index_by_id(strategy_id)
        self.strategies[idx] = copy.deepcopy(data)
        self.strategies[idx]["id"] = strategy_id
        self.save()        

    # Clone Strategy
    # ------------------------------------------------------------------
    def clone(self, old_id: int) -> int:
        old = next((s for s in self.strategies if s["id"] == old_id), None)
        if not old:
            raise ValueError(f"No strategy found with id '{old_id}'")

        new_data = copy.deepcopy(old)
        new_data["id"] = self._generate_new_id()
        new_data["run"] = False #Disable automatic run

        self.strategies.append(new_data)
        self.save()
        return new_data["id"]
    
    # Delete Strategy
    # ------------------------------------------------------------------
    def delete(self, strategy_id: int) -> None:
        self.strategies = [s for s in self.strategies if s["id"] != strategy_id]
        self.save()
    
    #Function to create a list of all pairs and their intervals
    # ------------------------------------------------------------------
    def generate_pairs_intervals(self) -> list:
        result = {}
        for s in self.strategies: #run trough all the stratagies
            #Creat a dicionary structure for each pair and candle interval
            s1 = s["Symbol1"]
            s2 = s["Symbol2"]
            pair = f"{s1}{s2}" 
            if not pair in result: #If unique add
                result[pair] = {
                    "Symbol1" : s1,
                    "Symbol2" : s2,
                    "Intervals" : []
                }
            base_interval = s["CandleInterval"]
            if not base_interval in result[pair]["Intervals"]:#Check if unique
                result[pair]["Intervals"].append(base_interval) #Add to the list of intervals

            for key, value in s.items(): #Go trough all keys to find DynamicBuy and Sell
                if "Dynamic" in key: #check if it is the list of indicators
                    for ind in value: #go trough the list
                        interval = ind.get("Interval") #Get if exists else it will be None value
                        if interval is None:
                            continue
                        if interval not in self.interval_list:
                            continue
                        if interval not in result[pair]["Intervals"]: #Check if unique
                            result[pair]["Intervals"].append(interval) #Add to the list of intervals

        return result
    
    # Change Logger
    # ==================================================================
    def _log_changes(self, old_list, new_list):
        #Logs only differences between old and new strategy sets.
        if not old_list:
            self.logger.info("Initial strategy file created.")
            return
        changes = get_changes(new_list, old_list)
        if changes != None:
            self.logger.info(changes)
    
    # Helpers
    # ==================================================================
    def _ensure_ids_unique(self):
        #Prevents corrupted files with duplicate IDs.
        seen = set()
        for s in self.strategies:
            sid = s.get("id")
            if sid in seen:
                sid = self._generate_new_id()
                s["id"] = sid
            seen.add(sid)

    def _generate_new_id(self) -> int:
        used = {s.get("id") for s in self.strategies}
        new_id = 0
        while new_id in used:
            new_id += 1
        return new_id
    
    def _get_index_by_id(self, strategy_id):
        for idx, s in enumerate(self.strategies):
                if s["id"] == strategy_id:
                    return idx        
        return None
