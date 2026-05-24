from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # adjust if needed

# ---- DATA FILES ----

# ---- LOG FILES ----
LOG_PATH_PYTH      = BASE_DIR / "logs" / "pyth.log"

# URLs
BASE_BENCH_URL= "https://benchmarks.pyth.network"
BASE_HERMES_URL= "https://hermes.pyth.network"

HIST_KLINE_URL= f"{BASE_BENCH_URL}/v1/shims/tradingview/history" 
CONFIG_URL= f"{BASE_BENCH_URL}/v1/shims/tradingview/config" 

PRICE_FEED_ID_URL = f"{BASE_HERMES_URL}/v2/price_feeds"
PRICE_LAST_URL = f"{BASE_HERMES_URL}/v2/updates/price/latest"

STREAM_URL = f"{BASE_HERMES_URL}/v2/updates/price/latest"