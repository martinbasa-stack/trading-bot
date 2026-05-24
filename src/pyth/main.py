from .manager import PythDataManager
from .constants import LOG_PATH_PYTH

from src.settings.main import strategies_obj

import logging


# Create a logger for this module
logger = logging.getLogger("pyth")
logger.setLevel(logging.INFO)

# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_PYTH)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

pyth_data_obj = PythDataManager(
    get_pairs=strategies_obj.get_pairs
)

