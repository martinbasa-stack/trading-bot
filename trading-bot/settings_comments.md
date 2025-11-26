Settings
General Settings structure
```python
    "strategyUpdate": 11,               # Update in seconds for running main thread 
    "liveTradeAging": 600,              # limit in seconds for open trade to be discarded (Live trades only)
    "histDataUpdate": 300,              # update in minutes for fetching historical data (if old data is detected the history data will be updated before this time)
    "pingUpdate": 10,                   # interval in minutes for pinging the Websocet connection and checking stream subscriptions
    "websocetManageLoopRuntime": 1.0,   # interval in seconds for running the websocet threed loop checking for new commands from main loop 
    "klineStreamLoopRuntime": 1.0,      # interval in seconds for running the stream thread loop
    "numOfHisCandles": 500,             # number of candle data returned when fetching historical data
    "host": "localhost",                # Flask server IP address  
    "Port": 5000,                       # Flask server Port
    "user": "robot",                    # Flask UI user  
    "password": "1",                    # Flask UI password (no encription!)
    "timeout": 10000,                   # Timeout in miliseconds for Websocet connection
    "reconnect_delay": 6,               # Reconect parameter in secondas for Binance API connection
    "API_KEY": "API_KEY",               # Binance API Key
    "API_SECRET": "API_SECRET",         # Binance API secret
    "useTelegram": true,                # Selection to send messages trough telegram
    "telegram_TOKEN": "TOKEN",          # telegram TOKEN
    "telegram_chatID": "hatID"          # telegram Chat ID of your bot
```
Strategy Setting
```python
    "id": 5,                            # unique solved in code No user edit available
    "name": "LIVE setup v01.01",        # name for user setup as desired
    "type": "AdvancedDCA",              # Type of strategy prepared for upgrades
    "Symbol1": "BTC",                   # Symbol1 of a Pair
    "Symbol2": "USDC",                  # Symbol2 of a Pair
    "run": true,                        # if False the strategy is paused
    "paperTrading": false,              # if true the trades are saved in seperate trade tabel and not send to API
    "candleCloseOnly": false,           # if true trades only at the candle close no intra candle trades
    "CandleInterval": "4h",             # candle interval for Dip and Pump detection ()indicators have theyr own
    "NumOfCandlesForLookback": 12,      # Maximum amount of candels to look back for finding min/max value to calculate Dip/Pump
    "timeLimitNewOrder": 600,           # Time in seconds for a new trade to be enabled if candleCloseOnly than this is a tolerance to open trade
    "assetManagerTarget": "Account",    # The target for managingbalances 
                                        #    "None" -> only check if enough assets on balance
                                        #    "Account" -> uses maximum amout of assets asigned to it (in trades), option to limit how much assets will be left on account
                                        #    "Trades" -> difference from "Account" is that the minimum amount is calculated based on how much was acummulated by buying
    "assetManagerSymbol": 1,            # Select a symbol to save (changes spending limits of assets)
    "assetManageMaxSpendLimit": 2000.0, # Maximum amount of a symbol we are not saving that we can spend
    "assetManageMinSaveLimit": 10.0,    # Minimum amount of simbol we are saving that wil be saved
    "assetManagePercent": 1,            # changes assetManageMinSaveLimit values to be absolut or inpercantage of Enty/Exit trades
    "roundBuySellorder": 2,             # Rounding for Symbol2 
    "BuyBase": 150.0,                   # Base amount of Symbol2 used for buying
    "DipBuy": 2.2,                      # % price needs to fall(Dip) from Max price to execute a Buy
    "BuyMaxFactor": 60.0,               # % ammount a Base Buy can be incresed when Buying
    "MinWeight_Buy": 0,                 # Minimum Weight "DynamicBuy" indicators have to produce for executing a Buy
    "MinWeight_Sell": 2,                # Minimum Weight "DynamicSell" indicators have to produce for executing a Sell
    "SellBase": 250.0,                  # Base amount of Symbol2 used for selling
    "TakeProfit": 2.5,                  # % price needs to rise(Pump) from Min price to execute a Sell
    "SellMaxFactor": 60.0,              # % ammount a Base Sell can be incresed when Selling
    "BuyMin": 100.0,                    # minimum amount to Buy in case no more availabe assets (either on account or limited by parameter)
    "SellMin": 100.0                    # minimum amount to Sell in case no more availabe assets (either on account or limited by parameter)
    "DynamicBuy":                       # List of indicators for buying
    "DynamicSell":                      # List of indicators for selling
```
Indicator Settings
```python
    "Type": "AvrageEntry",              # Type of indicator:
                                        #    - SMA Simple Moving Average
                                        #    - EMA Exponential Moving Average
                                        #    - BB Bollinger bands (Std dev is default at 2 and uses SMA)
                                        #    - RSI Relative Strengsh Index
                                        #    - ROC Rate Of Change
                                        #    - ADX Average Directional Movement Index
                                        #    - F&G Fear & Gread from Alternative.me (BTC)
                                        #    - AvrageCost Average Cost on your trades
                                        #    - AvrageEntry Average Entry on your BUY trades
                                        #    - AvrageExit Average Exit on your SELL trades
                                        #    - Price
    "Interval": "1d",                   # for TA indicators that use it an option can be selected
    "Enable": true,                     # Enable factor for calculating how much to increase a Base Buy/Sell 
    "Weight": 2,                        # Weight this indicator will produce when condition is enabled
    "BlockTradeOffset": -1.0,           # % the trigger value will be offseted
    "Value": 0,                         # Input value of TA indicator that uses it
    "Value2": 0,                        # Not Used
    "Value3": 0,                        # Not Used
    "Value4": 0,                        # Not Used
    "OutputSelect": "Upper",            # Selector for indicator output (exemple Bollinger bands)
    "Comparator": "Below",              # comparator between trigger and indicator output
    "Trigger": 0.0,                     # Trigger value for indicators that use triggers
    "TriggerSelect": "Price",           # Selsctor of a trigger (SMA and EMA can chose between Price or other SMAs)
    "Factor": 40.0,                     # % of delta (trigger - output) to increse the Base Buy/Sell
    "Max": 50.0                         # % limit maximum factor from this indicator
```

