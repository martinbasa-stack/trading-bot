
---

# 🚀 Advanced DCA Algorithmic Trading Bot

### **Version 2.0**

Automated algorithmic trading bot using an **Advanced DCA (Dollar-Cost Averaging) strategy**.
The bot can trade on **Binance CEX** or on **Solana** blockchain using **Raydium DEX** swaps.
The bot buys dips and sells pumps with optional **dynamic order adjustment**, indicator-based triggers, backtesting with intracandle price simulation, basic charting, integrated Telegram alerts, multi-threaded runtime, and a Flask UI dashboard.


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
* [📌 Version 2.0 Notice & Roadmap](#-version-20-notice--roadmap)

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
* **Binance stream thread** (Binance price updates)
* **WebSocket management thread** (Binance account updates, order fills)
* **Pyth stream thread** (onchain price updates)
* **Utiliti loop** (historical data managment and telegram bot)
* **Main trading loop** (Runs main bot strategies)


### ✔ Trade Integration

* Local trade table with CSV persistence
* Paper-trading mode included

### ✔ Binance Integration

* Live streams
* Live account & order updates

### ✔ On-chain Integration

* Supported chain **Solana**
* Securely encrypted mnemonic phrase 
    * Mnemonic phrase exists only in **RAM** after it is unlocked
    * Password protected -> Password is **irretrievable** does not exist in the program
    * Geanarate new wallet
    
* Live streams
* Live account & order updates

### ✔ Telegram Integration

* Trade notifications
* Error alerts
* Requested status messages

### ✔ Automatic Historical Data Loading

* Self-updating CSV historical files
* Auto-cleanup of old data

---

# ⚙️ Program Architecture

```
┌────────────────────────┐
│     Utiliti Thread      │  → Runs historical data updates and telegram bot
└────────────────────────┘

┌─────────────────────┐
│  Main trading loop   │  → Runs main bot strategies
└─────────────────────┘

┌──────────────────┐
│  Flask Thread     │  → Web UI / settings / logs
└──────────────────┘

┌──────────────────────┐
│  Pyth Stream Therea   │  → Price feed for onchain trading
└──────────────────────┘

┌───────────────────────────────────────┐
│  Binance WebSocket Management Thread   │ → Balances, trades, account events
└───────────────────────────────────────┘

┌──────────────────────────────┐
│   Binance Stream Thread       │ → Price feeds, OHLC updates
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
│   ├── credentials.json       # Encrypted credentials such as API,... Password and User are hashed
│   └── strategies.bak         # Backup of strategies
│
├── /data                      # Program-generated and managed data wallet encryption
├── /logs                      # Log files
│
├── /src
│   │
│   ├── /assets            # Asset management
│   │   ├── analyzer.py    # Asset analysis logic
│   │   ├── manager.py     # Asset balance manager
│   │   └── models.py
│   │
│   ├── /backtester            # Backtester logic
│   │   ├── main.py            # Runing the backtester
│   │   ├── models.py          
│   │   └── sequencer.py       # Logic for time and history candle symulation
│   │
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
│   ├── /Pyth                  # On chain historical kline data and stream
│   │   ├── constants.py       
│   │   ├── main.py            # Class and logger
│   │   ├── manager.py         # Managing of REST api data and stream data monitoring
│   │   ├── models.py         
│   │   └── stream.py          # Class with thread and websocket connection for stream
│   │
│   ├── /settings              # General and strategy settings
│   │   ├── changes.py         # Detects changes between old and new settings
│   │   ├── credentials.py     # Credentials encryption
│   │   ├── general.py         # General settings class
│   │   ├── main.py            # Class declarations
│   │   ├── strategy_convertors.py  # Dict <-> Dataclass converters
│   │   └── strategies.py      # Strategy settings manager
│   │
│   ├── /solana_api            # Solana chain integration
│   │   │
│   │   ├── /raydium           # Communication with Raydium
│   │   │   ├── constants.py
│   │   │   └── swap.py        # Transaction generation from Raydium
│   │   │
│   │   ├── /solana_tracker    # Unused data pooling
│   │   │   ├── constants.py     
│   │   │   └── fetch_kline.py
│   │   │
│   │   ├── /record_HL         # Last high/low tracking after trades
│   │   │   ├── manager.py     # High/Low record manager
│   │   │   └── models.py
│   │   │
│   │   ├── /tokens            # Managing on-chain token data [symbol, mint addres, decimals]
│   │   │   ├── manager.py     # Adding new tokens storing so file,...
│   │   │   ├── models.py
│   │   │   └── token_data.py  # Fetching on-chain data of token 
│   │   │
│   │   ├── /utils
│   │   │   ├── round.py       # Custom round function
│   │   │   └── storage.py     # JSON storage utilities
│   │   │
│   │   ├── /wallet            # On-chain interactions 
│   │   │   ├── balances.py    # Fetching wallet balances of stored tokens
│   │   │   ├── executor.py    # Signing and sending transactions, reading transaction status
│   │   │   └── models.py  
│   │   │
│   │   ├── constants.py        
│   │   ├── main.py            # Class
│   │   └── manager.py         # Managing wallet interaction sending trades reciving results. Main interaction point with the rest of the program.
│   │
│   ├── /strategy              # Main trading strategy logic
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
│   │   ├── dca.py             # Core DCA trading logic & trigger generation
│   │   ├── models.py
│   │   ├── utils.py
│   │   └── run.py             # Strategy execution loop
│   │
│   ├── /telegram              # Telegram application
│   │   ├── main.py            # Class
│   │   ├── on_message.py      # Function to proces recived cmd.
│   │   ├── response_utils.py  # Generation of response messages on recived cmds.
│   │   └── services.py        # Managing recived and send messages
│   │
│   ├── /utils
│   │   └── storage.py         # JSON storage utilities
│   │
│   ├── /wallet                # Wallet managment
│   │   ├── create.py          # Wallet creation and encryption.
│   │   ├── evm.py             # Prepared for future
│   │   ├── main.py            # Class
│   │   ├── solana.py          # Solana wallet Keypair
│   │   ├── utils.py           # Saving loading from .json, key deriviation.
│   │   └── vault.py           # Mnemonic seed phrase decryption and managment.
│   │
│   ├── models.py          
│   └── constants.py   
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
#### ``/backtester``
* Run trough history data and execute trades for backtesting your strategy.

#### `/assets`
* Manages account balances
* ``analyzer.py`` Calculates available amount of assets.

#### ``/binanceAPI``
* ``/stream`` Manages Stream communication with Binance
* ``/websocket`` Manages WebSocket communication with Binance
    * Sends trade orders
* Performs reconnection logic

#### ``/flask``
* ``routes.py`` All Flask UI routes
    * Serves /templates and /static
* ``views.py`` Generate data for UI 

#### `/marke_history`
* `/fear_gread`
    * Manages storage of Fear and Gread data
    * Fetch new data from Alternative.me

* `/price`
    * Loads/Saves kLine historical data
    * Manages kLine historical ``.csv`` files
    * Delivers kLine tables to other classes for computing
    * `run()` function takes care for data refresh
        * Purges old data files
        * request for new data
* `main.py`
    * Two price classes exist here for Binance and Pyth
    * Data updates are called from here.
    * Asynch task is running here.

#### `/pyth`
* `stream.py` manages stream connection internal class
* `manager.py` Manages data for the rest of the program


#### ``/settings``
* ``credentials.py`` Loads/Saves encrypted credentials
* ``general.py`` Loads/Saves general settings 
* ``strategies.py`` Loads/Saves strategy settings
    * Manages adding/removing strategies
* Logs every change to settings
* Delivers data from settings to other classes
    * list of IDs
    * list of all Interval used etc.

#### ``/solana_api``
* ``/raydium`` Interface for Raydium swap
    * Transaction routing.
    * Versioned transaction creation.
* ``/tokens`` Manages onchain data for tokens. User has to create them using **mint** addres
* ``/wallet`` Onchain execution Transaction signing,...
* ``manager.py`` 
    * Point of interaction with the rest of the program.
    * Sending trades 
    * Updating executed trades

#### ``/strategy``
* Core DCA strategy logic
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

#### ``/telegram`` 
* Sends message
* Recives commands

#### ``/wallet`` 
* Manages wallet encryption and decryption
* ***Mnemonic phrase*** and ***Keypair*** only lives in RAM while program is running

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

Username and password are configured and encrypted `credentials.json`.

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

### 4. Configure API keys in `credentials.json`
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

## Credentials
```json
{
    "user": "$2b$12$7O8Zn.gPDu53xVPY.OG7sefrQQAmYAyIhFM7Liurb/VF7sEvnkjAW",
    "password": "$2b$12$3y/1K720NyNseS2bhqMfIepHaA.PnptOjQ8hTdmLEoCAgE49m6BO2",
    "B_API_KEY": "API_KEY",
    "B_API_SECRET": "API_SECRET",
    "telegram_TOKEN": "telegram_TOKEN",
    "telegram_chatID": "telegram_chatID"
}
```

## Settings

All settings can be changed in Flask UI

```json
{
    "strategyUpdate": 11,
    "liveTradeAging": 600,
    "histDataUpdate": 300,
    "pingUpdate": 10,
    "statusUpdate": 6,
    "websocetManageLoopRuntime": 1.0,
    "klineStreamLoopRuntime": 1.0,
    "numOfHisCandles": 700,
    "host": "0.0.0.0",
    "Port": 5000,
    "timeout": 10000,
    "reconnect_delay": 6,
    "sol_slippage_bps": 10,
    "sol_price_impact_lim": 0.1,
    "sol_timeout": 10,
    "useTelegram": true
}
```

## Strategy Settings Example

```json
{
    "id": 5,
    "name": "LIVE setup v01.01",
    "type": "Binance_CEX",
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
<a id="#version-20-notice--roadmap"></a>

# 📌 Version 2.0 Notice & Roadmap

This is **Version 2.0**, updated for operation on-chain and on binance Exchange.

### Updates

* Add Solana chain
* Add Pyth data pooling
* telegram bot recieves commands
* Improved web UI

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

