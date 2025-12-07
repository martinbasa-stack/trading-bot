import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # adjust if needed
# ---- CONFIG FILES ----
FILE_PATH_STRATEGY = BASE_DIR / "config" / "strategies.json"
FILE_PATH_BASIC   = BASE_DIR / "config" / "settings.json"

# ---- DATA FILES ----
FILE_PATH_EXCHANGE_INFO = BASE_DIR / "data" / "_exchange_info_data.json"
FILE_PATH_USER_DATA_JSON = BASE_DIR / "data" / "_userdata.json"
FILE_PATH_USER_DATA_CSV  = BASE_DIR / "data" / "_userdata.csv"
FILE_PATH_HIST_STRATEGY  = BASE_DIR / "data" / "_histStrategyVal.json"
FILE_PATH_FEAR_GREAD     = BASE_DIR / "data" / "_fearAndGreed.json"

# ---- LOG FILES ----
LOG_PATH_SETTINGS    = BASE_DIR / "logs" / "settings_change.log"
LOG_PATH_MAIN        = BASE_DIR / "logs" / "main.log"
LOG_PATH_STRATEGY    = BASE_DIR / "logs" / "strategy.log"
LOG_PATH_BINANCE_API = BASE_DIR / "logs" / "Binance_API.log"
LOG_PATH_APP         = BASE_DIR / "logs" / "app.log"

INTERVAL_LIST = ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h"]    #For Streams
INDICATOR_INTERVAL_LIST = ["15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]    #For Indicator
#table columns headers
TRADE_TABLE_COL_TIMESTAMP = 0
TRADE_TABLE_COL_ID = 1
TRADE_TABLE_COL_SYMBOL_1 = 2
TRADE_TABLE_COL_ASSET_S1_QT = 3
TRADE_TABLE_COL_SYMBOL_2 = 4
TRADE_TABLE_COL_ASSET_S2_QT = 5
TRADE_TABLE_COL_PRICE = 6
TRADE_TABLE_COL_MAX = 7
TRADE_TABLE_COL_MIN = 8
TRADE_TABLE_COL_LOOKBACK = 9
TRADE_TABLE_COL_AVG_COST = 10
TRADE_TABLE_COL_CHANGE = 11
TRADE_TABLE_COL_COMMISION = 12
TRADE_TABLE_COL_COMMISION_ASSET = 13

#columns 0 = TmestampOpen, 1 = open, 2 = high, 3 = low, 4 = Close, 5 = volume, 6 = time close
KLINE_TABLE_COL_TIMESTAMP_OPEN = 0
KLINE_TABLE_COL_OPEN = 1
KLINE_TABLE_COL_HIGH = 2
KLINE_TABLE_COL_LOW = 3
KLINE_TABLE_COL_CLOSE = 4
KLINE_TABLE_COL_VOLUME_S1 = 5
KLINE_TABLE_COL_TIMESTAMP_CLOSE = 6
KLINE_TABLE_COL_VOLUME_S2 = 7
KLINE_TABLE_COL_TAKER_S1 = 8
KLINE_TABLE_COL_TAKER_S2 = 9

