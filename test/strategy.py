from.constants import(
    LOG_PATH_STRATEGY,
    FILE_PATH_HIST_STRATEGY,
    FILE_PATH_FEAR_GREAD
)
from .binance_API import my_balances, klinStreamdData, sendTrade, fetch_userData, fetch_histData, read_exchange_info
from .settings import settings_class, strategies_class
from .history import history_class, PairHistory, IntervalData
from .trades import trade_manager_class, Trade, TradeTable
from .record_high_low.highlow import HighLowManager
from .fear_gread.fear_gread import FearAndGread

import logging
from datetime import datetime, timezone

import numpy as np
import talib as ta

#get current time data
now_utc = datetime.now(timezone.utc)
timestamp_seconds = int(now_utc.timestamp())

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_STRATEGY, mode="a")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#Globals
advanceDCAstatus= {}
#Create object to storr all history data and high low records
record =  HighLowManager(path=FILE_PATH_HIST_STRATEGY, get_list_of_id_pair_func=strategies_class.id_pair_list)
fear_gread = FearAndGread(path=FILE_PATH_FEAR_GREAD)

def _calcIndicators(side, strategySettings, activeStrategyData, avarageCost, avarageEntry, avarageExit, LastPrice :float, history_pair: PairHistory, fear_gread: int):
    try:
        if not strategySettings[f"Dynamic{side}"]:
            return True, 0, activeStrategyData
        if not strategySettings[f"Dynamic{side}"][0]:
            return True, 0, activeStrategyData
        cumWeight = 0
        sumFactor = 0.0
        valToCompare = 0.0
        activeStrategyData[side] = {} #Create a data set
        pair = f"{strategySettings["Symbol1"]}{strategySettings["Symbol2"]}"
        for index, dynSet in enumerate(strategySettings[f"Dynamic{side}"]):  
            interval = dynSet["Interval"]
            indValue = dynSet["Value"]
            close = history_pair.intervals[interval].close
            low = history_pair.intervals[interval].low
            high = history_pair.intervals[interval].high
            IndexWeight = 0
            dividerForChange = 0 #for factor calc for index with positive limit range likr RSI
            triggOffset = 0
            textDisplay = ""
            match dynSet["Type"]: #Logic for different indicator types
                case s if "SMA" in s: #Simple movaing avradge logic            
                    temp = ta.SMA(close,indValue) 
                    valToCompare = temp[-1]
                    match dynSet["TriggerSelect"]:
                        case "Price":
                            triggVal = LastPrice
                            textDisplay = f"{s} {indValue} {interval} | Price"
                        case "SMA":
                            trigTemp = ta.SMA(close,int(dynSet["Trigger"]))
                            triggVal = trigTemp[-1]
                            textDisplay = f"{s} {indValue} {interval} | SMA {dynSet["Trigger"]} {interval}"
                        case "EMA":
                            trigTemp = ta.EMA(close,int(dynSet["Trigger"]))
                            triggVal = trigTemp[-1]
                            textDisplay = f"{s} {indValue} {interval} | EMA {dynSet["Trigger"]} {interval}"
                        case _:
                            triggVal = LastPrice
                            textDisplay = f"{s} {indValue} {interval} | Price"
                    dividerForChange = valToCompare     
                    triggOffset = dynSet["BlockTradeOffset"] 
                case s if "EMA" in s: #Exponential movaing avradge logic
                    temp = ta.EMA(close,indValue) 
                    valToCompare = temp[-1]
                    match dynSet["TriggerSelect"]:
                        case "Price":
                            triggVal = LastPrice
                            textDisplay = f"{s} {indValue} {interval} | Price"
                        case "SMA":
                            trigTemp = ta.SMA(close,int(dynSet["Trigger"]))
                            triggVal = trigTemp[-1]
                            textDisplay = f"{s} {indValue} {interval} | SMA {dynSet["Trigger"]} {interval}"
                        case "EMA":
                            trigTemp = ta.EMA(close,int(dynSet["Trigger"]))
                            triggVal = trigTemp[-1]
                            textDisplay = f"{s} {indValue} {interval} | EMA {dynSet["Trigger"]} {interval}"
                        case _:
                            triggVal = LastPrice
                            textDisplay = f"{s} {indValue} {interval} | Price"
                    dividerForChange = valToCompare
                    triggOffset = dynSet["BlockTradeOffset"]
                case s if "RSI" in s: #¸RSI logic
                    temp = ta.RSI(close,indValue) 
                    valToCompare = round(temp[-1],2)
                    triggVal = dynSet["Trigger"]
                    textDisplay = f"{s} {indValue} {interval} | Trigger"
                    dividerForChange = 100
                case s if "ROC" in s: #ROC logic
                    temp = ta.ROC(close,indValue) 
                    valToCompare = round(temp[-1],4)
                    triggVal = dynSet["Trigger"]
                    textDisplay = f"{s} {indValue} {interval} | Trigger"
                    dividerForChange = 1

                case s if "ADX" in s: #ADX logic
                    temp = ta.ADX(high, low, close,indValue) 
                    valToCompare = round(temp[-1],2)
                    triggVal = dynSet["Trigger"]
                    textDisplay = f"{s} {indValue} {interval} | Trigger"
                    dividerForChange = 100

                case s if "AvrageCost" in s: #Avradge cost of all trades
                    valToCompare = avarageCost 
                    triggVal = LastPrice
                    dividerForChange = valToCompare
                    triggOffset = dynSet["BlockTradeOffset"]
                    textDisplay = f"Average Cost | Price"
                    indValue = 0

                case s if "AvrageEntry" in s: #Avradge entry BUY logic
                    valToCompare = avarageEntry
                    triggVal = LastPrice
                    dividerForChange = valToCompare
                    triggOffset = dynSet["BlockTradeOffset"]
                    textDisplay = f"Average Entry | Price"
                    indValue = 0
                    
                case s if "AvrageExit" in s: #Avradge exit SELL logic
                    valToCompare = avarageExit
                    triggVal = LastPrice  
                    dividerForChange = valToCompare
                    triggOffset = dynSet["BlockTradeOffset"]
                    textDisplay = f"Average Exit | Price"
                    indValue = 0

                case s if "Price" in s: #Price logic works like limit order
                    valToCompare = LastPrice
                    triggVal = dynSet["Trigger"]
                    dividerForChange = valToCompare
                    textDisplay = f"Price | Trigger"
                    indValue = 0

                case s if "F&G" in s: #Feart and gread index
                    valToCompare = float(fear_gread) 
                    triggVal = dynSet["Trigger"]
                    dividerForChange = 100
                    textDisplay = f"Fear & Fread | Trigger"
                    indValue = 0
                
                case s if "BB" in s: #Boolinger bands nbdev-up-down both at default 2
                    upperband, middleband, lowerband = ta.BBANDS(close,timeperiod=indValue)
                    match dynSet["OutputSelect"]: #select trigger if 1 = Upper bound if 2 = lower bound else middle bound
                        case "Upper":
                            temp = upperband
                            textDisplay = f"BB Upper | Price"
                        case "Lower":
                            temp = lowerband
                            textDisplay = f"BB Lower | Price"
                        case _:
                            temp = middleband   
                            textDisplay = f"BB Middle | Price"             
                    valToCompare = temp[-1]
                    triggVal = LastPrice
                    dividerForChange = valToCompare
                    triggOffset = dynSet["BlockTradeOffset"]

                case s:
                    break #Go out of loop
            #Initialise data
            activeStrategyData[side][index] = {} #initiate active strategy data for preview  
            #remove numpy stuff
            triggOffset = float(triggOffset)
            triggVal = float(triggVal)
            valToCompare = float(valToCompare)
            dividerForChange = float(dividerForChange)
            offsetedTrigger = (triggOffset/100.0 + 1.0) *triggVal #offset trigger value for trade block 
            #check if trade is ENABLED by index with adding weight
            if dynSet["Comparator"] == "Above": # Check side for logic "Above" -> BLOCK if price below trigger 
                if valToCompare > offsetedTrigger: 
                    IndexWeight = dynSet["Weight"] #Add weight to enable trade
            else:
                if valToCompare < offsetedTrigger: 
                    IndexWeight = dynSet["Weight"] #Add weight to enable trade
            cumWeight = cumWeight + IndexWeight # Add to cumulative weight for end comparisment
            changeFromTrigger = 0 
            if dividerForChange != 0: #check that trigger is positive if not price change revers calculation 
                changeFromTrigger = (valToCompare - triggVal)/dividerForChange #Calc price change from trigger -Down +Up 
            else: 
                changeFromTrigger = 1 #set to 1 this is when no data for avradges

            factor = changeFromTrigger * dynSet["Factor"] #multiply by factor %
            if dynSet["Comparator"] == "Below": # Check side for logic comparisment to reverse
                factor = -factor     #reverse factor only positive is accepted

            activeStrategyData[side][index]["Factor"]= round(factor,2)    # write for info before limiting   
            factor = min(factor, dynSet["Max"]) #Limit to max factor                  
            factor = max(factor, 0) # limit to postitive value only if not enabled set to 0
            if not dynSet["Enable"]: factor = 0

            sumFactor = sumFactor + factor #Add to the end factor   
            temp = valToCompare
            countForRound = 2
            while temp < 1 and temp > 0:
                temp = temp*10
                countForRound +=1
            #save data             textDisplay
            activeStrategyData[side][index]["valToCompare"]= round(valToCompare,countForRound)
            activeStrategyData[side][index]["Type"]= dynSet["Type"]
            activeStrategyData[side][index]["Enable"]= dynSet["Enable"]
            activeStrategyData[side][index]["Blocking Trade"]= dynSet["Weight"] > IndexWeight
            activeStrategyData[side][index]["Weight"]= dynSet["Weight"]
            activeStrategyData[side][index]["WeightActual"]= IndexWeight
            activeStrategyData[side][index]["Delta"]= round(changeFromTrigger,2)
            activeStrategyData[side][index]["Value"]= indValue
            activeStrategyData[side][index]["Value2"]= dynSet["Value2"]
            activeStrategyData[side][index]["Value3"]= dynSet["Value3"]
            activeStrategyData[side][index]["Value4"]= dynSet["Value4"]
            activeStrategyData[side][index]["textDisplay"]= textDisplay
            activeStrategyData[side][index]["Comparator"]= dynSet["Comparator"]
            activeStrategyData[side][index]["Interval"]= interval
            activeStrategyData[side][index]["Trigger"]= round(triggVal, strategySettings["roundBuySellorder"])     #save trigger value
            activeStrategyData[side][index]["Trigger Offset"]=  round(offsetedTrigger, strategySettings["roundBuySellorder"])    #save trigger value

        activeStrategyData[f"Weight_{side}"] = cumWeight #Add value of cumulative weight of all index
        TradeEn = cumWeight >= strategySettings[f"MinWeight_{side}"]
        return TradeEn, sumFactor, activeStrategyData

    except Exception as e:
        logger.error(f"calcDynOrder() error: {e}")

#Asset manager
def _assetManager(strategySettings, BalanceSymbol1, BalanceSymbol2, dynFactorBuy, dynFactorSell, avarageEntry, avarageExit, avarageCost, LastPrice):
    S1balanceOK = True
    S2balanceOK = True
    MAXSpendLimit = strategySettings["assetManageMaxSpendLimit"]
    MINSaveLimit = strategySettings["assetManageMinSaveLimit"]
    toBuy = strategySettings["BuyBase"]*(1+dynFactorBuy/100) #desired amount to buy
    toSell = strategySettings["SellBase"]*(1+dynFactorSell/100)
    AvailableS1Assets = toSell/LastPrice
    AvailableS2Assets = toBuy
    #Basic limit on whole balance if not paper trading
    if not strategySettings["paperTrading"]:
        toBuy = min(toBuy,BalanceSymbol2*0.99) #*0,99 is to keep at least 1% on so trades do not Fail
        toSell = min(toSell,BalanceSymbol1*LastPrice*0.99) #*0,99 is to keep at least 1% on so trades do not Fail            
        AvailableS1Assets = BalanceSymbol1
        AvailableS2Assets = BalanceSymbol2

    #assetManageMaxSpendLimit if 0 = no limits make the max as big as sell/buy plus all trades sum
    if strategySettings["assetManagerSymbol"] == 1: #Save symbol 1 and spend symbol 2
        if MAXSpendLimit == 0: MAXSpendLimit = toBuy + abs(avarageCost["sumS2"])
    else:
        if MAXSpendLimit == 0: MAXSpendLimit = toSell + abs(avarageCost["sumS1"])

    match strategySettings["assetManagerTarget"]:
        case "Account":
            if strategySettings["assetManagerSymbol"] == 1: #Save symbol 1 and spend symbol 2
                #Limit spending of asset
                AvailableS2Assets = MAXSpendLimit + avarageCost["sumS2"] # sumS2 is negative when spent
                #Limit minimum account ballance
                if strategySettings["assetManagePercent"]: #if true calculate in percantage
                    #Calculate all Buys minus pecentage of all buys
                    AvailableS1Assets = BalanceSymbol1 - (avarageEntry["sumS1"]* MINSaveLimit/100) 
                else: #else calculate in absolute values
                    AvailableS1Assets = BalanceSymbol1 - MINSaveLimit
            else: #Save Symbol 2 and spend Symbol 1
                #Limit minimum account ballance 
                if strategySettings["assetManagePercent"]: #if true calculate in percantage
                    #Calculate all Sells minus pecentage of all Sell
                    AvailableS2Assets = BalanceSymbol2 - ( abs(avarageExit["sumS2"]) * MINSaveLimit/100) 
                else:
                    AvailableS2Assets = BalanceSymbol2 - MINSaveLimit
                #Limit spending of asset
                AvailableS1Assets = MAXSpendLimit + avarageCost["sumS1"]# sumS1 is negative when spent
            #Limit toBuy and toSell to the availabla assets
            toBuy = min(toBuy, AvailableS2Assets) 
            toSell = min(toSell, AvailableS1Assets*LastPrice ) 
        case "Trades":
            if strategySettings["assetManagerSymbol"] == 1: #Save symbol 1 and spend symbol 2
                #Limit spending of asset
                AvailableS2Assets = MAXSpendLimit + avarageCost["sumS2"] # sumS2 is negative when spent
                #Limit minimum saved
                if strategySettings["assetManagePercent"]: #if true calculate in percantage
                    #Calculate all trades minus pecentage of all buys
                    AvailableS1Assets = avarageCost["sumS1"] - (avarageEntry["sumS1"]* MINSaveLimit/100) 
                else: #else calculate in absolute values
                    AvailableS1Assets = avarageCost["sumS1"] - MINSaveLimit
            else: #Save Symbol 2 and spend Symbol 1
                #Limit minimum saved 
                if strategySettings["assetManagePercent"]: #if true calculate in percantage
                    #Calculate all Sells minus pecentage of all Sell
                    AvailableS2Assets =  avarageCost["sumS2"] - (abs(avarageExit["sumS2"]) * MINSaveLimit/100)
                else:
                    AvailableS2Assets =  avarageCost["sumS2"] - MINSaveLimit  #SumS2 is negative when spent
                #Limit spending of asset 
                AvailableS1Assets = MAXSpendLimit + avarageCost["sumS1"] #sumS1 is negative when spent
            #Limit toBuy and toSell to the availabla assets
            toBuy = min(toBuy, AvailableS2Assets) 
            toSell = min(toSell, AvailableS1Assets*LastPrice ) 
            
    #Limit to positive values
    toBuy = max(0,toBuy)
    toSell = max(0,toSell)    
    #check for minumim from exchange
    minBuy = strategySettings["BuyMin"]
    minSell = strategySettings["SellMin"]
    exchange_info_data = read_exchange_info()
    if len(exchange_info_data):
        Pair = f"{strategySettings["Symbol1"]}{strategySettings["Symbol2"]}"
        if Pair in exchange_info_data:
            minBuy = max(minBuy, exchange_info_data[Pair]["min_qty"])
            minSell = max(minSell, exchange_info_data[Pair]["min_qty"])
    #Final limit depending on balance on exchange
    if toBuy <  minBuy: #Can reduce order for 10%if necesary
        S2balanceOK = False    
    if toSell < minSell: #Can reduce order for 10%if necesary
        S1balanceOK = False
    toBuy = round(toBuy,strategySettings["roundBuySellorder"])
    toSell = round(toSell,strategySettings["roundBuySellorder"])
    #print(f"toBuy {toBuy}, S2balanceOK {S2balanceOK}, toSell {toSell}, S1balanceOK {S1balanceOK}")
    return toBuy, S2balanceOK, toSell, S1balanceOK, AvailableS2Assets, AvailableS1Assets

def _avgCost_pnl(last_close, trade_table: list[Trade]):
    position = 0.0        # net S1  position, signed
    cost_basis = 0.0      # absolute S2 that backs the position (>= 0)
    realized_pnl = 0.0

    for trade in trade_table:        
        qty_S1 = trade.quantity1  # S1 amount (signed)
        qty_S2 = trade.quantity2  # S2 amount (signed)

        # Opening when flat
        if position == 0:
            position = qty_S1
            cost_basis = abs(qty_S2)
            continue

        # Are we adding to the current side or reducing it?
        same_side = (position > 0 and qty_S1 > 0) or (position < 0 and qty_S1 < 0)
        # avg cost per unit (always positive)
        avg_cost = cost_basis / abs(position) if position != 0 else 0.0

        if same_side:
            # increase existing position: add absolute S2 to cost_basis
            position += qty_S1
            cost_basis += abs(qty_S2)
        else:
            # reducing (or closing + flipping)
            reduce_amount = min(abs(qty_S1), abs(position))
            removed_cost = reduce_amount * avg_cost                       # S2 removed from cost basis
            proceeds = abs(qty_S2) * (reduce_amount / abs(qty_S1))            # S2 corresponding to the closed portion

            # realized PnL depends on whether we closed a long or closed a short
            if position > 0 and qty_S1 < 0:
                # closing long: we sold now -> realized = proceeds - removed_cost
                realized_pnl += proceeds - removed_cost
            elif position < 0 and qty_S1 > 0:
                # closing short: we bought now -> realized = removed_cost - proceeds
                realized_pnl += removed_cost - proceeds
            else:
                # defensive — should not occur
                pass

            # remove cost from basis, update position
            cost_basis -= removed_cost
            position += qty_S1

            # fully closed
            if position == 0:
                cost_basis = 0.0
            else:
                # If the trade had a remainder that opens a new position
                # remaining_usdc = abs(usdc) - proceeds  (>= 0)
                # this remaining USDC becomes the new cost basis for the new side
                if (position > 0 and qty_S1 > 0) or (position < 0 and qty_S1 < 0):
                    remaining_usdc = abs(qty_S2) - proceeds
                    cost_basis = remaining_usdc

    # finalize avg cost and unrealized
    avg_cost = cost_basis / abs(position) if position != 0 else 0.0
    if position > 0:
        unrealized_pnl = position * (last_close - avg_cost)
    elif position < 0:
        unrealized_pnl = abs(position) * (avg_cost - last_close)
    else:
        unrealized_pnl = 0.0

    return unrealized_pnl, realized_pnl, avg_cost, cost_basis

#Main strategy logic
def _advanceDCA(strategy, BalanceSymbol1, BalanceSymbol2, record_class: HighLowManager, history_pair: PairHistory, fear_gread: int, trade_table: list[Trade]) -> Trade:
    if not strategy["run"]:
        return
    #Create active data to pass to UI
    activeStrategyData = {}
    #get current time data
    now_utc = datetime.now(timezone.utc)
    timestamp_seconds = int(now_utc.timestamp())
    #Create Index in dictionary to save max value
    global  advanceDCAstatus
    
    try:
        #path to candlestick history
        id= strategy["id"]
        s1 = strategy["Symbol1"]
        s2 = strategy["Symbol2"]
        pair = f"{s1}{s2}"
        record_id = f"{id}_{pair}"
        paper_trade = strategy["paperTrading"]
        rec = record_class.get(record_id) 
        hist_data : IntervalData = history_pair.intervals[strategy["CandleInterval"]]

        if not hist_data:
            return
        time_close = hist_data.time_close
        high =  hist_data.high
        low =  hist_data.low

        avarageCost = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        avarageEntry = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        avarageExit = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        realizedPnL = 0.0
        unrealizedPnL = 0.0
        totalPnL = 0.0
        totalPnLpercent = 0.0
        #Get last trade data -----------------------------------------------------
        if paper_trade: #Generate file path
            trade_id = "Paper"
        else:
            trade_id = "Open"
        last_trade: Trade = [] 
        if trade_table != None:
            for trade in trade_table:
                last_trade = trade
                avarageCost["sumS1"] += trade.quantity1
                avarageCost["sumS2"] += trade.quantity2
                if trade.quantity1 > 0.0:#Buys
                    avarageEntry["sumS1"] += abs(trade.quantity1)
                    avarageEntry["sumS2"] += abs(trade.quantity2)
                else:#Sells
                    avarageExit["sumS1"] += abs(trade.quantity1)
                    avarageExit["sumS2"] += abs(trade.quantity2)
                
            #Get trade data for calculation avradge cost and profit and loss         
            unrealizedPnL, realizedPnL, avarageCost["avg"], cost_basis = _avgCost_pnl(rec.close, trade_table)
            totalPnL = unrealizedPnL + realizedPnL
            
            totalPnLpercent = (totalPnL / abs(cost_basis)) * 100 if cost_basis != 0 else 0
            #Avradge entry and exit
            if avarageEntry["sumS1"] != 0:
                avarageEntry["avg"] = avarageEntry["sumS2"]/avarageEntry["sumS1"]
            if avarageExit["sumS1"] != 0:
                avarageExit["avg"] = avarageExit["sumS2"]/avarageExit["sumS1"]
            
        newTradeEn = True     
        lookBack = strategy["NumOfCandlesForLookback"]
        
        # check if price went above the last buy to reset max
        if last_trade: #chack if we have a trade
            #Enable new trade if min time passed from last one
            newTradeEn = (timestamp_seconds - int(last_trade.timestamp/1000)) > strategy["timeLimitNewOrder"]   
            
            count = 1
            for time in time_close: #Go trough history candles from past to now        
                #count untill candle time close is smaler than trade time count will be the new lookBack
                timeClose = int(time)
                timeLastTrade = int(last_trade.timestamp)
                if (timeClose < timeLastTrade):
                    count += 1 #count will point to the index of a candle wher trade happened    
            #If count is max lenght then trade was in last candle
            lookBack = int(len(high)) - int(count)
        
        lookBack = int(lookBack)#Numpy is making a mess for comparisments later
        maxLB = int(strategy["NumOfCandlesForLookback"]) #numpy is making a mess 
        #If trade was on last candle no need to generate max 
        if lookBack < 1: #Trade in the last candle #Save to dictionary maximum FOR BUY
            max_price =float(last_trade.price)
            max_price = max(max_price, rec.high)# Need check if the price went above             
            min_price =float(last_trade.price)
            min_price = min(min_price, rec.low) # Check if the price went below
        elif 0 < lookBack < maxLB:#Trade was done one candle ago and les than selected lookback              
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            high[len(high)-1 -lookBack] = max(rec.high ,last_trade.price)
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            low[len(low)-1 -lookBack] = min(rec.low,last_trade.price)  #Write last trade price to the TA anlasys arry to use it insted of actual value
            maxK = ta.MAX(high,lookBack+1) #Using lenght +1 to use the price that was added to array so it will compare current candle with price before
            max_price = maxK[-1]                
            minK = ta.MIN(low,lookBack+1)  
            min_price = minK[-1]              
        else: #Trade was done more than "NumOfCandlesForLookback" candles ago ta will get min and max                
            lookBack = maxLB
            maxK = ta.MAX(high,lookBack)
            max_price = maxK[-1]
            minK = ta.MIN(low,lookBack)
            min_price = minK[-1]
            record_class.reset(record_id, rec.close)

        if strategy["candleCloseOnly"] and newTradeEn:
            lastCandleClose = int(time_close[-2]/1000)
            newTradeEn = int(timestamp_seconds - lastCandleClose) < int(strategy["timeLimitNewOrder"]*0.9)

        #Go trough indexes
        #Dynamic BUY strategy factor and blocking trades
        dynBuyTradeEn, dynBuyFactor, activeStrategyData = _calcIndicators(
            "Buy", strategy, activeStrategyData, 
            avarageCost["avg"], avarageEntry["avg"], avarageExit["avg"], 
            rec.close, history_pair, fear_gread
            )
        #Dynamic SELL strategy factor
        dynSellTradeEn, dynSellFactor, activeStrategyData = _calcIndicators(
            "Sell", strategy, activeStrategyData, 
            avarageCost["avg"], avarageEntry["avg"], avarageExit["avg"], 
            rec.close, history_pair, fear_gread
            )
        #Factor MAX limitations
        dynBuyFactor = min(dynBuyFactor, strategy["BuyMaxFactor"])
        dynSellFactor = min(dynSellFactor, strategy["SellMaxFactor"])   
        #remove numpy
        dynSellFactor = float(dynSellFactor)
        dynBuyFactor = float(dynBuyFactor)     
        #-----------------------------Asset manager call--------------------------------------------------------------------------     
        toBuy, S2balanceOK, toSell, S1balanceOK, AvailableS2Assets, AvailableS1Assets = _assetManager(
            strategySettings = strategy, 
            BalanceSymbol1 = float(BalanceSymbol1), 
            BalanceSymbol2 = float(BalanceSymbol2), 
            dynFactorBuy = dynBuyFactor, 
            dynFactorSell = dynSellFactor, 
            avarageEntry = avarageEntry, 
            avarageExit = avarageExit, 
            avarageCost = avarageCost, 
            LastPrice = rec.close
            )
        
        #Remove Numpy stuf
        rec_close = float(rec.close)
        max_price = float(max_price)
        min_price= float(min_price)
        toBuy = float(toBuy)
        toSell = float(toSell)

        #Check changes form Max newBuyDropOk
        PercentCahangeFromMax = (max_price - rec_close)/max_price * 100
        newBuyDropOk = PercentCahangeFromMax > strategy["DipBuy"]
        #Check changes form Min newSellPumpOk
        PercentCahangeFromMin = (rec_close - min_price)/min_price * 100
        newSellPumpOk = PercentCahangeFromMin > strategy["TakeProfit"]
        
        #----------------------Cal buy/sel cmds----------------------------
        commission = 0.0 #create a column to bi filled when trade happens
        commission_asset = "NaN"  #create a column to bi filled when trade happens
        trade_trigger = False
        #Buy conditions
        if (newBuyDropOk and
                newTradeEn and
                dynBuyTradeEn and
                S2balanceOK):
            s1_qt = toBuy/rec_close
            s2_qt = -toBuy
            percent_change = PercentCahangeFromMax
            #Block sell
            newTradeEn = False
            trade_trigger = True #Trigger trade
            side = "BUY"
        #Sell conditions
        if (newSellPumpOk and
                newTradeEn and
                dynSellTradeEn and
                S1balanceOK):            
            s1_qt = -toSell/rec_close
            s2_qt = toSell
            percent_change = PercentCahangeFromMin
            trade_trigger = True #Trigger trade
            side = "SELL"
        trade = None
        #Write trade to table
        if trade_trigger:
            trade_trigger = False
            #Format trade
            trade: Trade = Trade(
                    timestamp=timestamp_seconds*1000,
                    idx=trade_id,
                    symbol1=s1,
                    quantity1=s1_qt,
                    symbol2=s2,
                    quantity2=s2_qt,
                    price=rec_close,
                    max_p=max_price,
                    min_p=min_price,
                    lookback=lookBack,
                    avg_cost=avarageCost["avg"],
                    change=percent_change,
                    commision=commission,
                    commision_symbol=commission_asset
                )

            #Reset saved values
            record_class.reset(record_id, rec.close)
            if not paper_trade:                    
                logger.info(f"New {side} order at : {datetime.fromtimestamp(int(timestamp_seconds))} \n "
                            f"strategy id : {id} \n "
                            f"pair : {s1}/{s2} \n "
                            f"{side} : {s1_qt} {s1} \n "
                            f"for : {s2_qt} {s2} \n "
                            f"at price : {rec_close} ")
        
        if True: #Save active strategy values 
            temp = toSell/rec_close
            countForRound = 2
            while temp < 1 and temp > 0:
                temp = temp*10
                countForRound +=1          
            #Save strategy values 
            activeStrategyData["Last Price"] = rec_close
            activeStrategyData[f"{strategy["Symbol1"]}"] = float(BalanceSymbol1)
            activeStrategyData[f"{strategy["Symbol2"]}"] = float(BalanceSymbol2)
            activeStrategyData["Avradge cost"] = round(avarageCost["avg"], strategy["roundBuySellorder"])
            activeStrategyData["Avradge entry"] = round(avarageEntry["avg"], strategy["roundBuySellorder"])
            activeStrategyData["Avradge exit"] = round(avarageExit["avg"], strategy["roundBuySellorder"])
            activeStrategyData["Cost SumS2"] = round(avarageCost["sumS2"], strategy["roundBuySellorder"])
            activeStrategyData["Entry SumS2"] = round(avarageEntry["sumS2"], strategy["roundBuySellorder"])
            activeStrategyData["Exit SumS2"] = round(avarageExit["sumS2"], strategy["roundBuySellorder"])
            activeStrategyData["Cost SumS1"] = round(avarageCost["sumS1"], countForRound)
            activeStrategyData["Entry SumS1"] = round(avarageEntry["sumS1"], countForRound)
            activeStrategyData["Exit SumS1"] = round(avarageExit["sumS1"], countForRound)
            activeStrategyData["Profit_Loss"] = round(totalPnL, strategy["roundBuySellorder"])
            activeStrategyData["Profit_LossPercent"] = round(totalPnLpercent, 2)
            activeStrategyData["PnL_realized"] = round(realizedPnL, strategy["roundBuySellorder"])
            activeStrategyData["PnL_unrealized"] = round(unrealizedPnL, strategy["roundBuySellorder"])
            activeStrategyData["Max Price"] = max_price
            activeStrategyData["Min Price"] = min_price
            activeStrategyData["Buy Ammount"] = toBuy
            activeStrategyData["Buy Factor"] =  round(dynBuyFactor,2) #save active data
            activeStrategyData["Buy Percente change"] = round(PercentCahangeFromMax,2)
            activeStrategyData["Sell Percente change"] = round(PercentCahangeFromMin,2)
            activeStrategyData["Sell Ammount Symbol1"] = round(toSell/rec_close, countForRound)
            activeStrategyData["Sell Ammount"] = toSell
            activeStrategyData["Sell Factor"] = round(dynSellFactor,2) #save active data

            #Save advanceDCAstatus
            #Get index of the trade strategy
            id = f"id_{strategy["id"]}"        
            advanceDCAstatus[id] = {} # initiate / if exist it will be cleared the strategy trade data
            #Fill base data                 
            advanceDCAstatus[id]["Symbol1"] = strategy["Symbol1"]
            advanceDCAstatus[id]["Symbol2"] = strategy["Symbol2"]
            advanceDCAstatus[id]["BuyBase"] = strategy["BuyBase"]
            advanceDCAstatus[id]["BuyMin"] = strategy["BuyMin"]
            advanceDCAstatus[id]["SellBase"] = strategy["SellBase"]
            advanceDCAstatus[id]["SellMin"] = strategy["SellMin"]
            advanceDCAstatus[id]["assetManagerTarget"] = strategy["assetManagerTarget"]
            advanceDCAstatus[id]["paperTrading"] = strategy["paperTrading"]
            advanceDCAstatus[id]["candleCloseOnly"] = strategy["candleCloseOnly"]
            advanceDCAstatus[id]["assetManagerSymbol"] = strategy[f"Symbol{strategy["assetManagerSymbol"]}"]
            advanceDCAstatus[id]["AvailableS2Assets"] = round(AvailableS2Assets, strategy["roundBuySellorder"])
            advanceDCAstatus[id]["AvailableS1Assets"] = round(AvailableS1Assets, countForRound)
            advanceDCAstatus[id]["BalanceSymbol2"] = round(float(BalanceSymbol2), strategy["roundBuySellorder"])
            advanceDCAstatus[id]["BalanceSymbol1"] = round(float(BalanceSymbol1), countForRound)
            advanceDCAstatus[id]["CandleInterval"] = strategy["CandleInterval"]
            advanceDCAstatus[id]["newTradeEn"] = newTradeEn
            advanceDCAstatus[id]["newBuyDropOk"] = newBuyDropOk
            advanceDCAstatus[id]["dynBuyTradeEn"] = dynBuyTradeEn
            advanceDCAstatus[id]["newBuyBalanceOk"] = S2balanceOK
            advanceDCAstatus[id]["MinWeight_Buy"] = strategy[f"MinWeight_Buy"]
            advanceDCAstatus[id]["newSellPumpOk"] = newSellPumpOk
            advanceDCAstatus[id]["newSellBalanceOk"] = S1balanceOK
            advanceDCAstatus[id]["dynSellTradeEn"] = dynSellTradeEn
            advanceDCAstatus[id]["MinWeight_Sell"] = strategy[f"MinWeight_Sell"]
            advanceDCAstatus[id]["type"] = strategy["type"]
            advanceDCAstatus[id]["name"] = f"{strategy["name"]} ID:{strategy["id"]} {strategy["Symbol1"]}/{strategy["Symbol2"]}"
            advanceDCAstatus[id]["data"] = activeStrategyData

        #print(f"Strategy status data: {advanceDCAstatus}")  
        # Wrtite status to logger 
        logger.debug(f"Strategy id {strategy["id"]} \n {strategy["name"]} on {strategy["Symbol1"]}/{strategy["Symbol2"]} pair \n"
                    f"last price: {rec_close}; \n Avrage cost: {avarageCost["avg"]}; \n Profit/Loss : {round(totalPnL,6)} | {round(totalPnLpercent,2)} %; \n Lookback val: {lookBack}"
                    )        
        return trade
    except Exception as e:
        logger.error(f"_advanceDCA() error: {e}")

def _update_hist():
    logger.debug(f"Fetching historical data")         
    #Fetch historical data for all pairs and needed intervals            
    pairs_intervals  = history_class.get_pairs_intervals() 
    for _, info in pairs_intervals.items():
        for interval in info["Intervals"]:
            s1 = info["Symbol1"]
            s2 = info["Symbol2"]
            #call function 
            kline_data = fetch_histData(
                Symbol1=s1,
                Symbol2=s2,
                Interval=interval,
                numData=settings_class.get("numOfHisCandles")                                     
                )   
            #Save to local data
            if kline_data !=None:
                history_class.update_interval(s1,s2,interval,kline_data) #Update data
    #Read user data
    fetch_userData() 

listOldPrices = {}
#Call the strategies -------------------------------------------------------------------------------------------
def strategyRun():
    global listOldPrices
    if True: #try:      
        #get current time data
        now_utc = datetime.now(timezone.utc)
        now_seconds = int(now_utc.timestamp())
        #Call cleenup
        record.cleanup()
        advanceDCAstatus.clear()
        fear_gread.update() #update Fear and Gread index
        #Run history manager returns true if history files need update
        hist_update_time = int(settings_class.get("histDataUpdate"))
        update_history = history_class.run(hist_update_time)
        
        trade_manager_class.cleanup()
        # Fetch history data
        if update_history:
            _update_hist()
            #src.loadHistKlineData(strategySettings) #read from .csv files and store in local table
        # Call All stratagies         
        for id_ in strategies_class.id_list(): #run trough all the stratagies
            strategy = strategies_class.get_by_id(id_)
            if str.lower(strategy["type"]) == str.lower("AdvancedDCA"): #run AdvancedDCA strategy only
                balanceS1 = 0
                balanceS2 = 0  
                s1 = strategy["Symbol1"]
                s2 = strategy["Symbol2"]            
                pair = f"{s1}{s2}"
                
                if s1 in my_balances:
                    balanceS1 = my_balances[s1]["Available"]
                if s2 in my_balances:
                    balanceS2 = my_balances[s2]["Available"] 
                if not klinStreamdData: #check if ther is any data from stream                    
                    logger.error(f"strategyRun() error: No price data for ALL")
                    break
                if pair not in klinStreamdData.keys(): #Check if the pair exists
                    logger.error(f"strategyRun() error: No price data for {pair} ")
                    continue
                if not ((timestamp_seconds - klinStreamdData[pair]["Time"]) < 180): #check the data is not older than 3 min
                    if not pair in listOldPrices: #Try not to spam logger
                        logger.error(f"strategyRun() error: Old price data for {pair} {datetime.fromtimestamp(int(klinStreamdData[pair]["Time"]))}")
                    else:                                
                        if listOldPrices[pair] != klinStreamdData[pair]["Time"]:
                            logger.error(f"strategyRun() error: Old price data for {pair} {datetime.fromtimestamp(int(klinStreamdData[pair]["Time"]))}")  
                    listOldPrices[pair] = klinStreamdData[pair]["Time"]
                    continue

                new_close = klinStreamdData[pair]["close"] #get close price
                history_class.update_last(pair,new_close)
                record.update(id_value=f"{id_}_{pair}", close=new_close)
                trade_table = trade_manager_class.get_table(id_)
                #Call Strategy function only if there is stream data
                trade = _advanceDCA(strategy, balanceS1, balanceS2, record_class=record, 
                                    history_pair=history_class.data[pair], 
                                    fear_gread=fear_gread.data.value,
                                    trade_table= trade_table)
                #Trade manager calls for executing trades
                if trade != None:
                    trade_manager_class.new_trade(id_, trade)
                open_trade = trade_manager_class.get_open(id_, settings_class.get("liveTradeAging"))
                if open_trade:
                    close_trade = sendTrade(open_trade)
                    if close_trade:
                        trade_manager_class.set_close(id_, close_trade)

    #except Exception as e: 
    #    logger.error(f"strategyRun() error: {e}")

def shutDown():
    record.save()

