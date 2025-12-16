
---

# 🚀 Advanced DCA Algorithmic Trading Bot

### **Version 1.4**

Automated algorithmic trading bot using an **Advanced DCA (Dollar-Cost Averaging) strategy**.
The bot buys dips and sells pumps with optional **dynamic order adjustment**, indicator-based triggers, backtesting with intracandle price simulation, basic charting, integrated Telegram alerts, multi-threaded runtime, and a Flask UI dashboard.

This is my **first major Python project**, and while fully functional, it may contains some unpolished areas.

---

# 📚 Table of Contents

* [✨ Features](#-features)
* [⚙️ Program Architecture](#️-program-architecture)
* [📁 Project Structure](#-project-structure)
* [🧠 Strategy Logic](#-strategy-logic)
* [🖥️ Flask Web UI](#️-flask-web-ui)
* [📥 Installation](#-installation)
* [📝 Requirements](#-requirements)
* [⚙️ Configuration](#️-configuration)
* [🤝 Donations](#-donations)
* [📌 Version 1.4 Notice & Roadmap](#-version-14-notice--roadmap)

---
# ✨ Features

### ✔ Advanced DCA Strategy

* Buys dips, sells pumps
* Adaptive order sizing using configurable indicators
* Dynamic blocking of trades based on technical conditions
* Independent BUY and SELL indicator systems

### ✔ Backtester

* Check your strategy on historical data
* Simulate intra candle data changes by moving price in pumps/dips steps

### ✔ Charts

* ``chartjs`` Basic charts for indicator display
* Trades visible on charts

### ✔ Full Multi-Threaded Runtime

* **Flask thread** (web UI)
* **Kline stream thread** (price updates)
* **WebSocket management thread** (account updates, order fills)
* **Main trading loop** (strategy execution)

### ✔ Binance Integration

* Live kline streams
* Live account & order updates
* Local trade table with CSV persistence
* Paper-trading mode included

### ✔ Telegram Integration

* Trade notifications
* Error alerts
* Status messages

### ✔ Automatic Historical Data Loading

* Self-updating CSV historical files
* Auto-cleanup of old data

---

# ⚙️ Program Architecture

```
┌──────────────────┐
│   Main Thread     │  → Runs all strategies continuously
└──────────────────┘

┌──────────────────┐
│  Flask Thread     │  → Web UI / settings / logs
└──────────────────┘

┌───────────────────────────────────────┐
│  Binance WebSocket Management Thread  │ → Balances, trades, account events
└───────────────────────────────────────┘

┌──────────────────────────────┐
│   Kline Stream Thread        │ → Price feeds, OHLC updates
└──────────────────────────────┘
```
---

# 📁 Project Structure

```
/project
│
├── /config
│   ├── settings.json          # General application settings
│   ├── strategies.json        # All stored strategies
│   └── strategies.bak         # Backup of strategies
│
├── /data                      # Program-generated and managed data
├── /logs                      # Log files
│
├── /src
│   ├── /backtester            # Backtester logic
│   │   ├── main.py            # Runing the backtester
│   │   ├── models.py          
│   │   └── sequencer.py       # Logic for time and history candle symulation
│   ├── /binance               # Binance API communication layer
│   │   ├── /stream
│   │   │   ├── manager.py     # Stream connection manager & data storage interface
│   │   │   ├── models.py      # Stream-related dataclasses
│   │   │   ├── stream.py      # Stream subscription, reconnection, etc.
│   │   │   └── thread.py      # Stream thread startup
│   │   │
│   │   └── /websocket
│   │       ├── connection.py # WebSocket connection, reconnection, send/receive logic
│   │       ├── manager.py    # WebSocket manager for command routing & formatting
│   │       ├── models.py
│   │       └── thread.py     # WebSocket thread startup
│   │
│   ├── /flask                # Flask web interface
│   │   ├── /chart            # Chart data formating
│   │   |   ├── format.py     # Format all
│   │   |   ├── indicators.py # Compute indicator values and format them for chart
│   │   |   └── models.py     
│   │   ├── form_utils.py     # Form-to-dict / form-to-dataclass converters
│   │   ├── log_utils.py
│   │   ├── routes.py         # Flask routes
│   │   └── views.py          # Data preparation for templates
│   │
│   ├── /market_history       # Historical data managment
│   │   ├── /price            # kLine price history
│   │   │   ├── manager.py    # Local kline data manager
│   │   │   ├── models.py
│   │   │   └── storage.py    # CSV file operations for kline data
│   │   │
│   │   ├── /fear_greed        # Fear & Greed index handling
│   │   │   ├── fear_greed.py
│   │   │   └── models.py
│   │   │
│   │   └── market.py          # Run function for data check and new data aquisition
│   │
│   ├── /settings              # General and strategy settings
│   │   ├── changes.py         # Detects changes between old and new settings
│   │   ├── general.py         # General settings class
│   │   ├── strategy_convertors.py  # Dict <-> Dataclass converters
│   │   └── strategies.py      # Strategy settings manager
│   │
│   ├── /strategy              # Main trading strategy logic
│   │   ├── /assets            # Asset management
│   │   │   ├── analyzer.py    # Asset analysis logic
│   │   │   ├── manager.py     # Asset balance manager
│   │   │   └── models.py
│   │   │
│   │   ├── /fear_greed        # Fear & Greed index handling
│   │   │   ├── fear_greed.py
│   │   │   └── models.py
│   │   │
│   │   ├── /indicators        # Technical indicator computations
│   │   │   ├── compute.py     # Indicator calculations (TA-Lib)
│   │   │   └── models.py
│   │   │
│   │   ├── /record_HL         # Last high/low tracking after trades
│   │   │   ├── manager.py     # High/Low record manager
│   │   │   └── models.py
│   │   │
│   │   ├── /trades            # Trade history and trade tables
│   │   │   ├── analyzer.py    # Trade analysis (PnL, averages, etc.)
│   │   │   ├── manager.py     # Trade data manager (store, update, save)
│   │   │   ├── models.py
│   │   │   └── storage.py     # CSV file operations for trades
│   │   │
│   │   ├── /utils
│   │   │   └── storage.py     # JSON storage utilities
│   │   │
│   │   ├── dca.py             # Core DCA trading logic & trigger generation
│   │   ├── models.py
│   │   └── run.py             # Strategy execution loop
│   │
│   ├── /telegram              # Telegram notification module
│   │   └── telegram.py
│   │
│   └── constants.py           # Global constants
│
├── /static                    # Frontend static files
│   ├── /css                   # Stylesheets
│   └── /js                    # Java Script
│
├── /templates                 # Flask HTML templates
│   └── /segments              # Reusable template fragments
│
├── app.py                     # Main application entry point
├── /test                      # Unit and integration tests
└── README.md

```
## Modules Overview
``/backtester``

* Run trough history data and execute trades for backtesting your strategy.

``/binanceAPI``

* ``/stream`` Manages Stream communication with Binance

* ``/websocket`` Manages WebSocket communication with Binance

    * Sends trade orders

* Performs reconnection logic


``/flask``

* ``routes.py`` All Flask UI routes
    * Serves /templates and /static

* ``views.py`` Generate data for UI 


`/marke_history`
* Loads/Saves kLine historical data
* Manages kLine historical ``.csv`` files
* Delivers kLine tables to other classes for computing
* `run()` function takes care for data refresh
    * Purges old data files
    * request for new data

``/settings``

* ``general.py`` Loads/Saves general settings
 
* ``strategies.py`` Loads/Saves strategy settings
    * Manages adding/removing strategies

* Logs every change to settings
* Delivers data from settings to other classes
    * list of IDs
    * list of all Interval used etc.



``/strategy``

* Core DCA strategy logic

* `/assets`
    * Manages account balances
    * ``analyzer.py`` Calculates available amount of assets.


* `/fear_gread`
    * Manages storage of Fear and Gread data
    * Fetch new data from Alternative.me

* `/indicators`
    * Comput triggers and buy factor from indicators

* `/record_JL`
    * Manages high and low value for each strategy for dip/pump trigger detection
    * Manages permanent storage to `.json`

* `/trades`
    * Manages trade tables
    * Servs trades for execution
        * Update closed ones
    * Purges old data files
    * ``analyzer.py`` get PnL and other analyzes from trade tables.

* ``dca.py``
    * Gathers all data and compute from other clases and generates a ``Trade``
    * Serves all trigger data for UI display.

* ``run.py`` 
    * checks data availability
    * runs trough all strategiess
    * sends open ``Trade`` for execution

``/telegram`` Sends message to bot

---

# 🧠 Strategy Logic

### Core Strategy (Advanced DCA)

* Detect price dip → buy
* Detect price pump → sell
* Optional **candle-close only trading**
* Adjustable limits for:

  * Buy/Sell scaling
  * Asset manager protection
  * Minimum/maximum order sizes
  * Indicator-based weighting (multi-indicator)

### Supported Indicators

* SMA / EMA
* Bollinger Bands
* RSI
* ROC
* ADX
* Fear & Greed Index (Alternative.me)
* Average Cost / Entry / Exit
* Price
* Custom trigger system (offsets, comparators, factor %, max %)

Program is generaly ready to add indicators from ``ta-lib``

---

# 🖥️ Flask Web UI

The web interface allows you to:

* Add/delete strategies
* Run/Stop strategies
* Edit strategy parameters
* Live view of trades
* Live status logs
* Manage settings

Username and password are configured in `settings.json`.

---

# 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/martinbasa-stack/trading-bot.git
cd advanced-dca-bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys in `settings.json`
Can be edited in Flask UI but require app restart to take effect
```
"API_KEY": "YOUR_API_KEY",
"API_SECRET": "YOUR_SECRET",
"telegram_TOKEN": "YOUR_TOKEN",
"telegram_chatID": "YOUR_CHAT_ID"
```

### 5. Start the bot

```bash
python app.py
```

Flask UI:
👉 [http://localhost:5000](http://localhost:5000)

***Default login credentials:***

* User: ``robot``

* Password: ``1``

⚠️(You should change these before using on network.)

---

# 📝 Requirements

### requirements.txt

```
flask
flask_simplelogin
binance-sdk-spot
numpy
ta-lib
fear-and-greed-crypto
python-telegram-bot
```
### Notes:

* ``ta-lib``

    Requires system-level dependencies on some platforms (Linux/macOS). \
    If installation fails, run:

    **Ubuntu/Debian:**
    ```
    sudo apt-get install libta-lib0 libta-lib0-dev
    ```

    **macOS (Homebrew):**
    ```
    brew install ta-lib
    ```

* ``fear-and-greed-crypto`` 

    Fetches the Fear & Greed Index from Alternative.me.

* ``binance-sdk-spot``

    A lightweight Binance Spot API wrapper.

* ``python-telegram-bot``

    Used to send trade alerts via Telegram.
---

# ⚙️ Configuration

## Settings

All settings can be changed in Flask UI

```json
    "strategyUpdate": 11,
    "liveTradeAging": 600,
    "histDataUpdate": 300,
    "pingUpdate": 10,
    "websocetManageLoopRuntime": 1.0,
    "klineStreamLoopRuntime": 1.0,
    "numOfHisCandles": 500,
    "host": "localhost",
    "Port": 5000,
    "user": "robot",
    "password": "1",
    "timeout": 10000,
    "reconnect_delay": 6,
    "API_KEY": "API_KEY",
    "API_SECRET": "API_SECRET",
    "useTelegram": true,
    "telegram_TOKEN": "TOKEN",
    "telegram_chatID": "chatID"
```

## Strategy Settings Example

```json
{
    "id": 5,
    "name": "LIVE setup v01.01",
    "type": "AdvancedDCA",
    "Symbol1": "BTC",
    "Symbol2": "USDC",
    "run": true,
    "paperTrading": false,
    "candleCloseOnly": false,
    "CandleInterval": "4h",
    "NumOfCandlesForLookback": 12,
    "timeLimitNewOrder": 600,
    "roundBuySellorder": 2,

    "assetManagerTarget": "Account",
    "assetManagerSymbol": 1,
    "assetManageMaxSpendLimit": 2000.0,
    "assetManageMinSaveLimit": 10.0,
    "assetManagePercent": 1,

    "DipBuy": 2.2,
    "BuyBase": 150.0,
    "MinWeight_Buy": 0,
    "BuyMaxFactor": 60.0,
    "BuyMin": 100.0,

    "TakeProfit": 2.5,
    "SellBase": 250.0,
    "MinWeight_Sell": 2,
    "SellMaxFactor": 60.0,
    "SellMin": 100.0,

    "DynamicBuy": [],
    "DynamicSell": []
}
```

## Indicator Settings Example

Indicators can adjust buy/sell orders dynamically, block trades, or act as triggers.
```json
{
    "Type": "SMA",
    "Interval": "1w",
    "Enable": true,
    "Weight": 0,
    "BlockTradeOffset": 0.0,
    "Value": 50,
    "Value2": 0,
    "Value3": 0,
    "Value4": 0,
    "OutputSelect": "Upper",
    "Comparator": "Above",
    "Trigger": 0.0,
    "TriggerSelect": "Price",
    "Factor": 100.0,
    "Max": 20.0
}
```

---

# 🤝 Donations

If you find this project helpful and want to support further development, consider donating:

| Network            | Address                                   |
| ---------------- | ----------------------------------------- |
| **SOL**          | `Do65RjYqrD8i3sMRJBRoJBhTxSvFjh6atVH9EiPrCS9Q` |
| **EVM** (Arbitrum pref.) | `0x8ca6c398F8Eedb42D3F0F1049d45AAe8517Aa9c9`                   |
| **BTC**    | `bc1q4hvhu392z5u94359lfeccae8m3j6g0tukswtny`                        |

Thank you for supporting open-source algorithmic trading tools! ❤️


---
<a id="#version-12-notice--roadmap"></a>

# 📌 Version 1.4 Notice & Roadmap

This is **Version 1.4**, my first full Python trading system. The python part is now full OOP.

### Updates

* Add charts
* Improved web UI
* Improved connection managment with Binance API
* Built-in backtester

### Shorfalls 

* Charts are a bit glitch while displaying tooltips.

### Planned Improvements (v1.5+)

* Add Simple Earn asset managment
* Improved web UI

### Known Issues
#### 1. Binance API Stream WebSocket Reconnect Issue

After losing connection, Binance refuses re-subscription to the same stream after reconnecting. 
Found that the ``global_stream_connections.stream_connections_map`` is still populated with old streams eaven after disconnecting and claering the ``connection`` and ``client`` class.


**Solution:**
Import the global variable and delete streams.
```python
from binance_common.websocket import global_stream_connections

self._strem_map = global_stream_connections.stream_connections_map

def _global_cleanup(self):
    try:
        for stream in list(self._strem_map.keys()):
            del self._strem_map[stream]
    except Exception as e:
        self._logger.error(f"StreamWorker error {stream}: {e}")
```

Thanks for your patience as this evolves into a polished, professional project.

---

