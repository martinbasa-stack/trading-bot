
---

# 🚀 Advanced DCA Algorithmic Trading Bot

### **Version 1.1**

Automated algorithmic trading bot using an **Advanced DCA (Dollar-Cost Averaging) strategy**.
The bot buys dips and sells pumps with optional **dynamic order adjustment**, indicator-based blocking, integrated Telegram alerts, multi-threaded runtime, and a Flask UI dashboard.

This is my **first major Python project**, and while fully functional, it still contains some unpolished areas.
A cleaner, fully OOP version is planned — see the roadmap below.

---

# 📚 Table of Contents

* [✨ Features](#features)
* [⚙️ Program Architecture](#️program-architecture)
* [📁 Project Structure](#project-structure)
* [🧠 Strategy Logic](#strategy-logic)
* [🖥️ Flask Web UI](#️flask-web-ui)
* [📥 Installation](#installation)
* [📝 Requirements](#requirements)
* [⚙️ Configuration](#️configuration)
* [🤝 Donations](#donations)
* [📌 Version 1.0 Notice & Roadmap](#version-10-notice--roadmap)

---

# ✨ Features

### ✔ Advanced DCA Strategy

* Buys dips, sells pumps
* Adaptive order sizing using configurable indicators
* Dynamic blocking of trades based on technical conditions
* Independent BUY and SELL indicator systems

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
│──/config
    │──settings.json      
    │──strategies.json      #All strategies
│──/data                    #data generated and managed by program
│──/logs                    #logg files
|──/src
    ├── /fear_gread         # FearAndGread class (updates, data storing,..) 
        ├── fear_gread.py
        ├── models.py
    ├── /flask              # Flask blueprints
        ├── form_utils.py   # Functions for form to dict transorms
        ├── routes.py     
        ├── views.py        # Data generation for passing to flask
    ├── /history            # Historical kLine data managment
        ├── manager.py      # class created oneced in __init__.py
        ├── models.py
        ├── storage.py      # File modification
    ├── /record_high_low    # Managment of last high low data after trade
        ├── highlow.py      # Class
        ├── models.py
    ├── /settings           # General and strategy settings managment
        ├── changes.py      # Detecting changes made after modification
        ├── general.py      # Class for general settings
        ├── strategies.py   # Class for strategy setting
    ├── /telegram           # Prepared
    ├── /trades             # Managing trade tables
        ├── manager.py      # Class
        ├── models.py
        ├── storage.py
    ├── /utils
        ├── storage.py      # File modification of .json used by classes
    ├── binanceAPI.py       # WebSocket management, Stream, Telegram integration
    ├── constants.py  
    ├── strategy.py         # Strategy engine, data logic
├── /static                 # CSS/JS files
├── /templates              # Flask templates
├── app.py                  # main start
└── README.md
```
## Modules Overview
``binanceAPI.py``

* Manages Stream/WebSocket communication with Binance

* Sends trade orders

* Performs reconnection logic

* Sends Telegram notifications

``/flask``

* All Flask UI routes

* Serves /templates and /static

* Fetch data for updates and delivers to responsable class

* Manages adding/removing strategies

``/settings``

* Loads/Saves general settings
 
* Loads/Saves strategy settings

* Logs every change to settings
* Delivers data from settings to other classes
    * list of IDs
    * list of all Interval used etc.

`/trades`
* Manages trade tables

* Servs trades for trades
    * Update closed ones

* Purges old data files

``strategy.py``

* Core DCA strategy logic

* Determines buy/sell signals

`/history`
* Loads/Saves historical data

* `run()` function takes care for data refresh

    * Purges old data files
    * request for new data

`/record_high_low`

* Manages high and low value for each strategy for dip/pump trigger detection

* Responsible for modification and reste of set values

* Manages permanent storage to `.json`


`/fear_gread`

* Manages storage of Fear and Gread data

* Fetch new data from Alternative.me


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

# 📌 Version 1.1 Notice & Roadmap

This is **Version 1.1**, my first full Python trading system.
While it works reliably, some parts are still not fully Pythonic. It is one step in the right dirrection.

### Updates

* The program functionality is still the same only program structure is changed
* Better file organisation
* Separation of some functions to classes
    * History manager
    * Trade manager
    * Settings managment 
    * Strategy managment
    * And some smaller ones 


### Current shortfalls

* Too many nested dictionaries
* Long monolithic functions
* Limited class usage
* Some inconsistent naming
* Early-stage architecture

### Planned Improvements (v1.2+)

* Full OOP rewrite (`Trade`, `Position`, `Strategy`, `Exchange`)
* `strategy.py` and `binance_API` module still needs complete rework 
* Pydantic models for config
* Plugin-based strategy system
* Built-in backtester
* Improved web UI
* Cleaner file structure

### Known Issues
#### 1. Binance API WebSocket Reconnect Issue

After losing connection, Binance sometimes refuses re-subscription to the same stream after reconnecting.

**Temporary Solution:**

The bot automatically switches to a different interval when reconnecting, which forces Binance to accept the new subscription.

Thanks for your patience as this evolves into a polished, professional project.

---

