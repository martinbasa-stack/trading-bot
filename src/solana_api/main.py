from .tokens.manager import TokenManager
from .manager import SolanaManager
from .constants import LOG_PATH_SOLANA

from src.wallet.main import solana_wallet
from src.settings.main import settings_obj

import logging

# Create a logger for this module
logger = logging.getLogger("solana")
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_SOLANA)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

solana_man_obj = SolanaManager(
    wallet_keys=solana_wallet,
    settings_get= settings_obj.get
)