from src.utils.storage import save_json, load_json
import logging
from pathlib import Path
from typing import Any, Dict


class SettingsManager:
    #Manage loading, updating and saving settings stored in a JSON file.
    #Automatically logs changes while masking sensitive fields. 
    SENSITIVE_KEYS = {"password", "API_KEY", "API_SECRET", "telegram_TOKEN"}

    def __init__(self, file_path: str, log_path: str):
        self.settings_path = Path(file_path)
        self.log_path = Path(log_path)

        # --- Logger Setup ---
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # prevent duplicate logs

        file_handler = logging.FileHandler(self.log_path, mode="a")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(file_handler)

        # Load settings immediately
        self._data: Dict[str, Any] = {}
        self._data = self._load()
    
    # Public 
    # ==================================================================

    #Read
    def get(self, key: str, default: Any = None) -> Any:
        #Get an individual setting.
        return self._data.get(key, default)

    def all(self) -> Dict[str, Any]:
        #Return all current settings.
        return self._data

    # -----------------------------------------------------------
    #Write
    def set(self, key: str, value: Any) -> None:
        #Set a setting and save immediately
        self._data[key] = value
        self._save()

    def update(self, kwval: dict) -> None:
        #Update multiple fields at once.
        for key, value in kwval.items():
            self._data[key] = value
        self._save()

    # Change Logger
    # ==================================================================
    def _log_changes(self, old_data):
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
            self.logger.info(f"Settings updated: {msg}")
        
    # Internal JSON I/O
    # ==================================================================
    def _load(self) -> Dict[str, Any]:
        #Load settings from the JSON file.
        try:
            if not self.settings_path.exists():
                self.logger.warning(f"Settings file not found, creating default empty file.")
                self.settings_path.write_text("{}")
            loda_data = load_json(self.settings_path)
            return loda_data
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return loda_data

    def _save(self) -> None:
        #Write settings back to JSON, log changes.
        try:
            old_data = self._load()
            save_json(self.settings_path, self._data)
            self._log_changes(old_data)            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")

    