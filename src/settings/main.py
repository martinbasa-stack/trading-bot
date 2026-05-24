from .general import SettingsManager
from .strategies import StrategyManager
from .credentials import CredentialsManager
from src.constants import(
    LOG_PATH_SETTINGS,
    FILE_PATH_BASIC,
    FILE_PATH_STRATEGY,
    INDICATOR_INTERVAL_LIST,
    FILE_PATH_CRED
)

import logging

# Configure logger
# Create a logger for this module
logger = logging.getLogger("settings")

# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_SETTINGS)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

strategies_obj = StrategyManager(file_path=FILE_PATH_STRATEGY, 
                             interval_list=INDICATOR_INTERVAL_LIST
                             )

settings_obj = SettingsManager(file_path=FILE_PATH_BASIC)

credentials_obj = CredentialsManager(FILE_PATH_CRED)