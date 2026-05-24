from src.utils.storage import save_json, load_json

import threading
import logging
from pathlib import Path
from typing import Any, Dict

# SettingsManager Class (long-living)
# ----------------------------------------------------------------------
class SettingsManager:
    """ (long-living) Class for storing and managin general settings
            saving and loading from .json file
            Main class that others depend on!
            initialized in __init__.py
    """
    #Manage loading, updating and saving settings stored in a JSON file.
    #Automatically logs changes while masking sensitive fields. 
    SENSITIVE_KEYS = {"password", "API_KEY", "API_SECRET", "telegram_TOKEN"}

    def __init__(self, file_path: str):  
        """ 
        Args:
            file_path(str): path to the .json file of all strategies
        """        
        self._settings_path = Path(file_path)
        #threading
        self._lock = threading.Lock()

        # --- Logger Setup ---
        self._logger = logging.getLogger("settings").getChild(self.__class__.__name__)

        # Load settings immediately
        self._data: Dict[str, Any] = {}
        self._data = self._load()
    
    # Internal JSON I/O
    # ==================================================================
    def _load(self) -> Dict[str, Any]:
        #Load settings from the JSON file.
        try:
            if not self._settings_path.exists():
                self._logger.warning(f"Settings file not found, creating default empty file.")
                self._settings_path.write_text("{}")
            loda_data = load_json(self._settings_path)
            return loda_data
        except Exception as e:
            self._logger.error(f"Error loading settings: {e}")
            return loda_data

    def _save(self) -> None:
        #Write settings back to JSON, log changes.
        try:
            old_data = self._load()
            save_json(self._settings_path, self._data)
            self._log_changes(old_data)            
        except Exception as e:
            self._logger.error(f"Error saving settings: {e}")

    # Public 
    # ==================================================================
    # Read one value
    # -----------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)
    # Read all values
    # -----------------------------------------------------------
    def all(self) -> Dict[str, Any]:
        with self._lock:
            return self._data

    # Write one value
    # -----------------------------------------------------------
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._save()

    # Write all / multiple
    # -----------------------------------------------------------
    def update(self, kwval: dict) -> None:
        with self._lock:
            for key, value in kwval.items():
                self._data[key] = value
            self._save()

    # Change Logger
    # ==================================================================
    def _log_changes(self, old_data: dict):
        # Determine changes
        changes = []
        for key, new_value in self._data.items():
            old_value = old_data.get(key)

            if old_value == new_value:
                continue

            if key in self.SENSITIVE_KEYS:
                changes.append(f"{key} changed (hidden value)")
            else:
                changes.append(f"{key}: {old_value} -> {new_value}")

        if changes:
            msg = " | ".join(changes)
            self._logger.info(f"Settings updated: {msg}")
        
    

    