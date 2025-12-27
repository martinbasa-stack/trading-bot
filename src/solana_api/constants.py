from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # adjust if needed

# ---- DATA FILES ----
FILE_PATH_SOLANA_TOKENS = BASE_DIR / "data" / "_solana_tokens.json"
FILE_PATH_SOLANA_WALLET = BASE_DIR / "data" / "_solana_wallet.json"

# ---- LOG FILES ----
LOG_PATH_SOLANA      = BASE_DIR / "logs" / "solana.log"

# ------ RPC -----
MAIN_RPC_URL = "https://api.mainnet-beta.solana.com"
