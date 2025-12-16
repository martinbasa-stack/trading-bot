from src.utils.storage import save_json, load_json
from .changes import get_changes
from .models import StrategyConfig, AssetManagerConfig, IndicatorConfig
from .strategy_convertors import dict_to_strategy, strategy_to_dict

import threading
import logging
import copy
from pathlib import Path
from typing import List, Any
import shutil

# StrategyManager Class (long-living)
# ----------------------------------------------------------------------
class StrategyManager:
    """ (long-living) Class for storing and managin settings of all strategies.
            Saving and loading from .json file.
                Main class that others depend on!
                initialized in __init__.py
    """
    #Manages reading, writing, updating and cloning strategy settings
    #with secure and detailed change logging.
    def __init__(self, 
                 file_path: str, 
                 log_path: str, 
                 interval_list: list):    
        """ 
        Args:
            file_path(str): 
                path to the .json file of all strategies
            log_path(str): 
                path to the log
            interval_list(list): 
                list of allowed intervals
        """        
        self._file_path = Path(file_path)
        self._log_path = Path(log_path)
        self._interval_list = interval_list
        #threading
        self._lock = threading.RLock()

        # --- Logger Setup ---
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False  # prevent duplicate logs

        _file_handler = logging.FileHandler(self._log_path, mode="a")
        _formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        _file_handler.setFormatter(_formatter)

        if not self._logger.handlers:
            self._logger.addHandler(_file_handler)

        # Load settings immediately
        self._strategies: List[StrategyConfig] = self._load_json()
        self._ensure_ids_unique()
    
    # Internal JSON I/O
    # ==================================================================
    def _load_json(self) -> List[StrategyConfig]:
        #Load strategies from disk or initialize empty file.
        
        if not self._file_path.exists():
            self._logger.critical(f"STRATEGY FILE MISSING: {self._file_path}")
            raise FileNotFoundError(self._file_path)
        if self._file_path.exists():
            backup = self._file_path.with_suffix(".bak")
            shutil.copy2(self._file_path, backup)

        try:
            raw = load_json(self._file_path)
            return [dict_to_strategy(x) for x in raw]
        except Exception as e:
            self._logger.error(f"Error loading strategies: {e}")

    def _save_json(self, data: list):
        #Write strategies to disk with safe logging.
        try:
            old = [strategy_to_dict(x) for x in self._strategies]
            json_ready = [strategy_to_dict(x) for x in data]
            save_json(self._file_path, json_ready)
            self._log_changes(old, json_ready)
        except Exception as e:
            self._logger.error(f"Error saving strategies: {e}")

    # Public 
    # ==================================================================
    def get_all_dict(self) -> list[dict]:
        """ 
        Returns:
            list[dict]:
                All strategies as dict.
        """     
        with self._lock:
            return [strategy_to_dict(s) for s in self._strategies]
    
    def get_all(self) -> list[StrategyConfig]:
        """ 
        Returns:
            list[StrategyConfig]:
                All strategies as StrategyConfig.
        """     
        with self._lock:
            return [s for s in self._strategies]
    
    #Get one strategy by its ID value
    # ------------------------------------------------------------------
    def get_by_id(self, strategy_id) -> StrategyConfig:
        """ 
        Args:
            strategy_id(Any):
                Unique strategy ID
        Returns:
            StrategyConfig:
                Strategy by its ID.
        """     
        with self._lock:
            idx = self._get_index_by_id(strategy_id)
            return self._strategies[idx]
        
    # Get one strategy by its ID value
    # ------------------------------------------------------------------
    def get_by_id_dict(self, strategy_id) -> dict:
        """ 
        Args:
            strategy_id(Any):
                Unique strategy ID
        Returns:
            dict:
                Strategy by its ID.
        """     
        with self._lock:
            idx = self._get_index_by_id(strategy_id)
            return strategy_to_dict(self._strategies[idx])
    
    #Get Asset Manager Configuration by strategy ID value
    # ------------------------------------------------------------------
    def get_am_config(self, strategy_id) -> AssetManagerConfig:   
        """ 
        Args:
            strategy_id(Any):
                Unique strategy ID
        Returns:
            AssetManagerConfig:
                Asset manager configuration by strategy ID.
        """      
        with self._lock:
            strategy:StrategyConfig = self.get_by_id(strategy_id)
        return strategy.asset_manager

    #Get buy indicators configuration by strategy ID value
    # ------------------------------------------------------------------
    def get_buy_indic_config(self, strategy_id) -> list[IndicatorConfig]:
        """ 
        Args:
            strategy_id(Any):
                Unique strategy ID
        Returns:
            list[IndicatorConfig]:
                List of BUY indicators configuration
        """      
        with self._lock:   
            strategy:StrategyConfig = self.get_by_id(strategy_id)
        return [i for i in strategy.indicators_buy]

    #Get sell indicators configuration by strategy ID value
    # ------------------------------------------------------------------
    def get_sell_indic_config(self, strategy_id: int) -> list[IndicatorConfig]:
        """ 
        Args:
            strategy_id(Any):
                Unique strategy ID
        Returns:
            list[IndicatorConfig]:
                List of SELL indicators configuration
        """       
        with self._lock:   
            strategy:StrategyConfig = self.get_by_id(strategy_id)
        return [i for i in strategy.indicators_sell]

    #return list of all strategy ID s
    # ------------------------------------------------------------------
    def get_id_list(self) -> list:  
        """ 
        Returns:
            list[Any]:
                List of strategy IDs
        """      
        with self._lock:      
            return [s.idx for s in self._strategies]
    
    #Return list of pairs with ID attached
    # ------------------------------------------------------------------
    def get_id_pair_list(self) -> list:
        """ 
        Returns:
            list[str]:
                List of strategy ID_pair
        """
        with self._lock:        
            list_out = []
            for s in self._strategies:
                pair = f"{s.idx}_{s.symbol1}{s.symbol2}"
                list_out.append(pair)
            return list_out

    # ------------------------------------------------------------------
    def save(self):
        """ 
        Save local data to file.
        """
        with self._lock:
            self._save_json(self._strategies)
    
    # Write to run no saving 
    # ------------------------------------------------------------------
    def set_run(self, strategy_id, value: bool) -> None:
        """ 
        Writes run without saving data to file.
        Args:
            strategy_id(Any):
                Unique strategy ID.
            value(bool):
                Valiue to RUN/STOP strategy.
        """

        with self._lock: 
            index = self._get_index_by_id(strategy_id)
            self._strategies[index].run = value

    # Write to paper trading no saving 
    # ------------------------------------------------------------------
    def set_paper_t(self, strategy_id: int, value: bool) -> None: 
        """ 
        Writes paper trading without saving data to file.
        Args:
            strategy_id(Any):
                Unique strategy ID.
            value(bool):
                Valiue set PAPER / LIVE trading mode of strategy.
        """
        with self._lock: 
            index = self._get_index_by_id(strategy_id)
            self._strategies[index].asset_manager.paper_t = value

 
    # Add Strategy
    # ------------------------------------------------------------------
    def add(self, data: StrategyConfig) -> Any:
        """ 
        Adds new strategy. Run = False to preven automatic start of strategy.
        Args:
            data(StrategyConfig):
                Strategy configuration
        Returns:
            Any:
                New strategy ID.
        """

        with self._lock:
            new_id = self._generate_new_id()
            data.idx = new_id
            data.run = False #Disable automatic run
            self._strategies.append(copy.deepcopy(data))
        self.save()
        return new_id

    # Update Strategy
    # ------------------------------------------------------------------
    def update(self, strategy_id, data: StrategyConfig):
        """ 
        Saves to an existing strategy. if it does not exist it will create new one.
        Args:
            data(StrategyConfig):
                Strategy configuration.
        """
        with self._lock:
            idx = self._get_index_by_id(strategy_id)
            if idx !=None:
                data.idx = strategy_id
                self._strategies[idx] = copy.deepcopy(data)
            else:                
                self._strategies.append(copy.deepcopy(data))
        self.save()        
    
    # Delete Strategy
    # ------------------------------------------------------------------
    def delete(self, strategy_id) -> None:
        """ 
        Removes strategy from local data and .json file.
        Args:
            strategy_id(Any):
                Strategy ID.
        """
        with self._lock:
            self._strategies = [s for s in self._strategies if s.idx != strategy_id]
        self.save()
    
    # Function to create a list of all pairs and their intervals
    # ------------------------------------------------------------------
    def generate_pairs_intervals(self) ->  dict[str, dict[str, object]]:
        """        
        Returns:
        dict[str, dict[str, object]]: Dictionary in the form:
        {
            "BTCUSDT": {
                "Symbol1": "BTC",
                "Symbol2": "USDT",
                "Intervals": ["5m", "1h", "1d"]
            },
            ...
        }
        """
        with self._lock:
            result = {}
            for s in self._strategies: #run trough all the stratagies
                #Creat a dicionary structure for each pair and candle interval
                s1 = s.symbol1
                s2 = s.symbol2
                pair = f"{s1}{s2}" 
                if not pair in result: #If unique add
                    result[pair] = {
                        "Symbol1" : s1,
                        "Symbol2" : s2,
                        "Intervals" : []
                    }
                base_interval = s.candle_interval
                if not base_interval in result[pair]["Intervals"]:#Check if unique
                    result[pair]["Intervals"].append(base_interval) #Add to the list of intervals

                # DynamicBuy
                for ind in s.indicators_buy:
                    if ind.interval in self._interval_list:
                        if ind.interval not in result[pair]["Intervals"]:
                            result[pair]["Intervals"].append(ind.interval)

                # DynamicSell
                for ind in s.indicators_sell:
                    if ind.interval in self._interval_list:
                        if ind.interval not in result[pair]["Intervals"]:
                            result[pair]["Intervals"].append(ind.interval)

            return result
    
    # Change Logger
    # ==================================================================
    def _log_changes(self, old_list :list[StrategyConfig], new_list:list[StrategyConfig]):
        #Logs only differences between old and new strategy sets.
        if not old_list:
            self._logger.info("Initial strategy file created.")
            return
        changes = get_changes(new_list, old_list)
        if changes != None:
            self._logger.info(changes)
    
    # Helpers
    # ==================================================================
    def _ensure_ids_unique(self):
        #Prevents corrupted files with duplicate IDs.
        seen = set()
        for s in self._strategies:
            sid = s.idx
            if sid in seen:
                sid = self._generate_new_id()
                s.idx = sid
            seen.add(sid)

    def _generate_new_id(self) -> int:
        used = {s.idx for s in self._strategies}
        new_id = 0
        while new_id in used:
            new_id += 1
        return new_id
    
    def _get_index_by_id(self, strategy_id):
        for idx, s in enumerate(self._strategies):
            if s.idx == strategy_id:
                return idx        
        return None