from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # adjust if needed

# ---- DATA FILES ----
FILE_PATH_ARB_TOKENS = BASE_DIR / "data" / "_arb_tokens.json"

# ---- LOG FILES ----
LOG_PATH_EVM      = BASE_DIR / "logs" / "evm.log"

# ------ RPC -----
ARB_MAIN_RPC_URL = "https://arb1.arbitrum.io/rpc"
