
---

# 🚀 Advanced DCA Algorithmic Trading Bot

### **Version 1.0**

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
    │──strategies.json    #All strategies
│──/data                  #data generated and managed by program
│──/logs                  #logg files
|──/src
    ├── binanceAPI.py     # WebSocket management, REST API, Telegram integration
    ├── constants.py  
    ├── flaskRoute.py     # Flask routes, templates, static files
    ├── settings.py       # Global settings + strategy settings manager
    ├── strategy.py       # Strategy engine, trade table, historical data logic
├── /static           # CSS/JS files
├── /templates        # Flask templates
├── app.py            # main start
└── README.md
```
## Modules Overview
``binanceAPI.py``

* Manages Stream/WebSocket communication with Binance

* Sends trade orders

* Performs reconnection logic

* Sends Telegram notifications

``flaskRoute.py``

* All Flask UI routes

* Serves /templates and /static

* Updates setting and sends to ``settings.py``

* Manages adding/removing strategies

``settings.py``

* Loads/Saves general settings
 
* Loads/Saves strategy settings

* Logs every change to settings

``strategy.py``

* Core DCA strategy logic

* Determines buy/sell signals

* Manages trade table and order execution

* Loads/Saves historical data

* Purges old data files


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

# 📌 Version 1.0 Notice & Roadmap

This is **Version 1.0**, my first full Python trading system.
While it works reliably, some parts are still not fully Pythonic.

### Current shortfalls

* Too many nested dictionaries
* Long monolithic functions
* Limited class usage
* Some inconsistent naming
* Early-stage architecture

### Planned Improvements (v1.1+)

* Full OOP rewrite (`Trade`, `Position`, `Strategy`, `Exchange`)
* Pydantic models for config
* Better logging
* Plugin-based strategy system
* Built-in backtester
* Improved web UI
* Async WebSocket support
* Cleaner file structure

### Known Issues
#### 1. Binance API WebSocket Reconnect Issue

After losing connection, Binance sometimes refuses re-subscription to the same stream after reconnecting.

**Temporary Solution:**

The bot automatically switches to a different interval when reconnecting, which forces Binance to accept the new subscription.

Thanks for your patience as this evolves into a polished, professional project.

---

