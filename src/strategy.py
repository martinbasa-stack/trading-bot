from .binance_API import my_balances, klinStreamdData, sendTrade, fetch_userData, fetch_histData, read_exchange_info
from.constants import(
    LOG_PATH_STRATEGY,
    FILE_PATH_HIST_STRATEGY,
    FILE_PATH_FEAR_GREAD,
    INDICATOR_INTERVAL_LIST,
    TRADE_TABLE_COL_TIMESTAMP,
    TRADE_TABLE_COL_ID,
    TRADE_TABLE_COL_SYMBOL_1,
    TRADE_TABLE_COL_ASSET_S1_QT,
    TRADE_TABLE_COL_SYMBOL_2,
    TRADE_TABLE_COL_ASSET_S2_QT,
    TRADE_TABLE_COL_PRICE,
    TRADE_TABLE_COL_MAX,
    TRADE_TABLE_COL_MIN,
    TRADE_TABLE_COL_LOOKBACK,
    TRADE_TABLE_COL_AVG_COST,
    TRADE_TABLE_COL_CHANGE,
    TRADE_TABLE_COL_COMMISION,
    TRADE_TABLE_COL_COMMISION_ASSET,    
    KLINE_TABLE_COL_TIMESTAMP_OPEN,
    KLINE_TABLE_COL_OPEN,
    KLINE_TABLE_COL_HIGH,
    KLINE_TABLE_COL_LOW,
    KLINE_TABLE_COL_CLOSE,
    KLINE_TABLE_COL_VOLUME_S1,
    KLINE_TABLE_COL_TIMESTAMP_CLOSE,
    KLINE_TABLE_COL_VOLUME_S2
)
from .settings import loadBsettings,loadStrSettings

import logging
import os
from datetime import datetime, timezone
import csv
import json

import numpy as np
import talib as ta
from fear_and_greed import FearAndGreedIndex


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
timeHistFetch = timestamp_seconds

#Only dictionary is passed normaly with from .x import
histStrategyVal = {}
historyKlineData = {} #Whole kLine data recived is keept here
localTradeTables = {}
tradeTablesView= {} 
advanceDCAstatus= {}
fearAndGreed={}

#Save at shut down and load at start histStrategyVal to a file
def _load_histStrategyVal():
    global histStrategyVal
    if not os.path.exists(FILE_PATH_HIST_STRATEGY):
        return
    with open(FILE_PATH_HIST_STRATEGY, "r") as jf: # save list of assets as JSON
        histStrategyVal = json.load(jf)        
    logger.debug("load_histStrategyVal done")

def _save_histStrategyVal():
    global histStrategyVal
    with open(FILE_PATH_HIST_STRATEGY, "w") as jf: # save list of assets as JSON
        json.dump(histStrategyVal, jf, ensure_ascii=False, indent=4)   
    logger.debug(f"save_histStrategyVal done {histStrategyVal}")

def _gefFearAndGread():
    try:
        global fearAndGreed    #save it to global for acces in strategy
        now_utc = datetime.now(timezone.utc)
        timestamp_seconds = int(now_utc.timestamp())  
        timeNewDataAvailable= 0 
        if os.path.exists(FILE_PATH_FEAR_GREAD):        
            with open(FILE_PATH_FEAR_GREAD, "r") as jf: # open load from JSON
                fearAndGreed = json.load(jf)
        if len(fearAndGreed):
            #Check if data is old
            timeNewDataAvailable= int(fearAndGreed["timestamp"]) + int(fearAndGreed["time_until_update"]) +60 #Write when new data will be available plus 60s
        if timestamp_seconds > timeNewDataAvailable:    #Get new data from server and save it
            # Create an instance of the FearAndGreedIndex
            fng_index = FearAndGreedIndex()
            #Get complete current data (value, classification, timestamp)
            fearAndGreed = fng_index.get_current_data()
            fearAndGreed["timestamp"] = timestamp_seconds
            with open(FILE_PATH_FEAR_GREAD, "w") as jf: # save  as JSON
                json.dump(fearAndGreed, jf, ensure_ascii=False, indent=4)   
            logger.debug(f"gefFearAndGread() Data: {fearAndGreed}")
    except Exception as e:
        logger.error(f"gefFearAndGread() error: {e}")

def _creatTradeTablesView():
    try:       
        global tradeTablesView      
        tradeTablesView.clear() #Cleare the whole table before creating

        for idKey in list(localTradeTables.keys()):
            if localTradeTables[idKey]["PaperTrading"]:  
                tradeTable = localTradeTables[idKey]["PaperTrades"]
            else:
                tradeTable = localTradeTables[idKey]["Trades"]

            tradeDatanew = []
            if tradeTable != None:
                reversed_arr  = tradeTable[::-1]#Reorder from new to old new at the top
                for i in reversed_arr:   # Formating of timestamp and converting all to string since it is only for display
                    tempTupple = (
                    str(datetime.fromtimestamp(int(i[TRADE_TABLE_COL_TIMESTAMP]/1000))), 
                    str(i[TRADE_TABLE_COL_ID]),
                    str(i[TRADE_TABLE_COL_SYMBOL_1]),
                    str(i[TRADE_TABLE_COL_ASSET_S1_QT]),
                    str(i[TRADE_TABLE_COL_SYMBOL_2]),
                    str(i[TRADE_TABLE_COL_ASSET_S2_QT]),
                    str(i[TRADE_TABLE_COL_PRICE]),
                    str(round(i[TRADE_TABLE_COL_CHANGE],2)),
                    str(i[TRADE_TABLE_COL_COMMISION]),
                    str(i[TRADE_TABLE_COL_COMMISION_ASSET])
                    )       
                    tradeDatanew.append(tempTupple)  

                tradeTablesView[idKey] = {} # initiate / if exist it will cleare the strategy trade data
                #Fill base data
                tradeTablesView[idKey]["Symbol1"] = localTradeTables[idKey]["Symbol1"]
                tradeTablesView[idKey]["Symbol2"] = localTradeTables[idKey]["Symbol2"]
                tradeTablesView[idKey]["CandleInterval"] = localTradeTables[idKey]["CandleInterval"]
                tradeTablesView[idKey]["type"] = localTradeTables[idKey]["type"]
                tradeTablesView[idKey]["paperTrading"] = localTradeTables[idKey]["PaperTrading"]
                tradeTablesView[idKey]["name"] = f"{localTradeTables[idKey]["name"]}_{localTradeTables[idKey]["Symbol1"]}_{localTradeTables[idKey]["Symbol2"]}"
                tradeTablesView[idKey]["trades"] = tradeDatanew       

    except Exception as e:
        logger.error(f"_creatTradeTablesView() error: {e}")

def _calcIndicators(side, strategySettings, activeStrategyData, avarageCost, avarageEntry, avarageExit, LastPrice):
    try:
        if len(strategySettings[f"Dynamic{side}"]) ==0:
            return True, 0,0, activeStrategyData
        if not strategySettings[f"Dynamic{side}"][0]:
            return True, 0,0, activeStrategyData
        cumWeight = 0
        sumFactor = 0.0
        valToCompare = 0.0
        activeStrategyData[side] = {} #Create a data set
        Pair = f"{strategySettings["Symbol1"]}{strategySettings["Symbol2"]}"
        for index, dynSet in enumerate(strategySettings[f"Dynamic{side}"]):  
            interval = dynSet["Interval"]
            indValue = dynSet["Value"]
            close = historyKlineData[Pair]["Intervals"][interval]["close"]
            low = historyKlineData[Pair]["Intervals"][interval]["low"]
            high = historyKlineData[Pair]["Intervals"][interval]["high"]
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
                    valToCompare = float(fearAndGreed["value"]) 
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

def _avgCost_pnl(LastPrice, tradeTable):
    position = 0.0        # net S1  position, signed
    cost_basis = 0.0      # absolute S2 that backs the position (>= 0)
    realized_pnl = 0.0

    for trade in tradeTable:
        qty_S1 = trade[TRADE_TABLE_COL_ASSET_S1_QT]  # S1 amount (signed)
        qty_S2 = trade[TRADE_TABLE_COL_ASSET_S2_QT]  # S2 amount (signed)

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
        unrealized_pnl = position * (LastPrice - avg_cost)
    elif position < 0:
        unrealized_pnl = abs(position) * (avg_cost - LastPrice)
    else:
        unrealized_pnl = 0.0

    return unrealized_pnl, realized_pnl, avg_cost, cost_basis

#Main strategy logic
def _advanceDCA(strategySettings, BalanceSymbol1, BalanceSymbol2, LastPrice):
    if not strategySettings["run"]:
        return
    #Create active data to pass to UI
    activeStrategyData = {}
    #get current time data
    now_utc = datetime.now(timezone.utc)
    timestamp_seconds = int(now_utc.timestamp())
    #Create Index in dictionary to save max value
    global histStrategyVal, advanceDCAstatus
    
    try:
        #path to candlestick history
        Pair = f"{strategySettings["Symbol1"]}{strategySettings["Symbol2"]}"
        #filePath = f"data/_{strategySettings["Symbol1"]}_{strategySettings["Symbol2"]}_candle_{strategySettings["CandleInterval"]}.csv"
        if not historyKlineData[Pair]["Intervals"][strategySettings["CandleInterval"]]:
            return
        strSaveValMax = f"{strategySettings["type"]}_{strategySettings["id"]}_{Pair}_max"    
        strSaveValMin = f"{strategySettings["type"]}_{strategySettings["id"]}_{Pair}_min"
        if not (strSaveValMax in histStrategyVal): histStrategyVal[strSaveValMax] = LastPrice #create if it does not exist
        if not (strSaveValMin in histStrategyVal): histStrategyVal[strSaveValMin] = LastPrice #create if it does not exist        
        if histStrategyVal[strSaveValMin] ==0: histStrategyVal[strSaveValMin] = LastPrice
        #my_histData = historyKlineData[Pair]["Intervals"][strategySettings["CandleInterval"]].copy()#np.genfromtxt(filePath, delimiter=",") #Create an array from csv
        timeStampClose = historyKlineData[Pair]["Intervals"][strategySettings["CandleInterval"]]["timeStampClose"]
        high =  historyKlineData[Pair]["Intervals"][strategySettings["CandleInterval"]]["high"]
        low =  historyKlineData[Pair]["Intervals"][strategySettings["CandleInterval"]]["low"]

        avarageCost = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        avarageEntry = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        avarageExit = {"avg" : 0.0, "sumS1" : 0.0, "sumS2" : 0.0}
        realizedPnL = 0.0
        unrealizedPnL = 0.0
        totalPnL = 0.0
        totalPnLpercent = 0.0
        my_tradeData = None
        #Get last trade data -----------------------------------------------------
        if strategySettings["paperTrading"]: #Generate file path
            my_tradeData = localTradeTables[strategySettings["id"]]["PaperTrades"]
        else:
            my_tradeData = localTradeTables[strategySettings["id"]]["Trades"]
        lastTrade = [] 
        if my_tradeData != None:
            for trade in my_tradeData:
                lastTrade = trade
                avarageCost["sumS1"] += trade[TRADE_TABLE_COL_ASSET_S1_QT]
                avarageCost["sumS2"] += trade[TRADE_TABLE_COL_ASSET_S2_QT]
                if trade[TRADE_TABLE_COL_ASSET_S1_QT] > 0.0:#Buys
                    avarageEntry["sumS1"] += abs(trade[TRADE_TABLE_COL_ASSET_S1_QT])
                    avarageEntry["sumS2"] += abs(trade[TRADE_TABLE_COL_ASSET_S2_QT])
                else:#Sells
                    avarageExit["sumS1"] += abs(trade[TRADE_TABLE_COL_ASSET_S1_QT])
                    avarageExit["sumS2"] += abs(trade[TRADE_TABLE_COL_ASSET_S2_QT])
                
            #Get trade data for calculation avradge cost and profit and loss         
            unrealizedPnL, realizedPnL, avarageCost["avg"], cost_basis = _avgCost_pnl(LastPrice, my_tradeData)
            totalPnL = unrealizedPnL + realizedPnL
            
            totalPnLpercent = (totalPnL / abs(cost_basis)) * 100 if cost_basis != 0 else 0
            #Avradge entry and exit
            if avarageEntry["sumS1"] != 0:
                avarageEntry["avg"] = avarageEntry["sumS2"]/avarageEntry["sumS1"]
            if avarageExit["sumS1"] != 0:
                avarageExit["avg"] = avarageExit["sumS2"]/avarageExit["sumS1"]
    
        else:
            my_tradeData = []

        newTradeEn = True     
        lookBack = strategySettings["NumOfCandlesForLookback"]
        
        # check if price went above the last buy to reset max
        if len(lastTrade) > 0: #chack if we have a trade
            #Enable new trade if min time passed from last one
            newTradeEn = (timestamp_seconds - int(lastTrade[TRADE_TABLE_COL_TIMESTAMP]/1000)) > strategySettings["timeLimitNewOrder"]   
            
            count = 1
            for time in timeStampClose: #Go trough history candles from past to now        
                #count untill candle time close is smaler than trade time count will be the new lookBack
                timeClose = int(time)
                timeLastTrade = int(lastTrade[TRADE_TABLE_COL_TIMESTAMP])
                if (timeClose < timeLastTrade):
                    count += 1 #count will point to the index of a candle wher trade happened    
            #If count is max lenght then trade was in last candle
            lookBack = int(len(high)) - int(count)
        
        lookBack = int(lookBack)#Numpy is making a mess for comparisments later
        maxLB = int(strategySettings["NumOfCandlesForLookback"]) #numpy is making a mess 
        #If trade was on last candle no need to generate max 
        if lookBack < 1: #Trade in the last candle #Save to dictionary maximum FOR BUY
            histStrategyVal[strSaveValMax] = max(histStrategyVal[strSaveValMax], LastPrice)
            maxPrice =float(lastTrade[TRADE_TABLE_COL_PRICE])
            maxPrice = max(maxPrice, histStrategyVal[strSaveValMax])# Need check if the price went above
            #Save to dictionary minumum value FOR SELL for minimum both have to be non 0
            histStrategyVal[strSaveValMin] = min(LastPrice,histStrategyVal[strSaveValMin])                
            minPrice =float(lastTrade[TRADE_TABLE_COL_PRICE])
            minPrice = min(minPrice, histStrategyVal[strSaveValMin]) # Check if the price went below
        elif 0 < lookBack < maxLB:#Trade was done one candle ago and les than selected lookback              
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            high[len(high)-1 -lookBack] = max(histStrategyVal[strSaveValMax] ,lastTrade[TRADE_TABLE_COL_PRICE])
            #Write last trade price to the TA anlasys arry to use it insted of actual value
            low[len(low)-1 -lookBack] = min(histStrategyVal[strSaveValMin],lastTrade[TRADE_TABLE_COL_PRICE])  #Write last trade price to the TA anlasys arry to use it insted of actual value
            maxK = ta.MAX(high,lookBack+1) #Using lenght +1 to use the price that was added to array so it will compare current candle with price before
            maxPrice = maxK[-1]                
            minK = ta.MIN(low,lookBack+1)  
            minPrice = minK[-1]              
        else: #Trade was done more than "NumOfCandlesForLookback" candles ago ta will get min and max                
            lookBack = maxLB
            maxK = ta.MAX(high,lookBack)
            maxPrice = maxK[-1]
            histStrategyVal[strSaveValMax] = LastPrice
            minK = ta.MIN(low,lookBack)
            minPrice = minK[-1]
            histStrategyVal[strSaveValMin] = LastPrice

        if strategySettings["candleCloseOnly"] and newTradeEn:
            lastCandleClose = int(timeStampClose[-2]/1000)
            newTradeEn = int(timestamp_seconds - lastCandleClose) < int(strategySettings["timeLimitNewOrder"]*0.9)

        #Go trough indexes
        #Dynamic BUY strategy factor and blocking trades
        dynBuyTradeEn, dynBuyFactor, activeStrategyData = _calcIndicators(
            "Buy", strategySettings, activeStrategyData, 
            avarageCost["avg"], avarageEntry["avg"], avarageExit["avg"], 
            LastPrice)
        #Dynamic SELL strategy factor
        dynSellTradeEn, dynSellFactor, activeStrategyData = _calcIndicators(
            "Sell", strategySettings, activeStrategyData, 
            avarageCost["avg"], avarageEntry["avg"], avarageExit["avg"], 
            LastPrice)
        #Factor MAX limitations
        dynBuyFactor = min(dynBuyFactor, strategySettings["BuyMaxFactor"])
        dynSellFactor = min(dynSellFactor, strategySettings["SellMaxFactor"])   
        #remove numpy
        dynSellFactor = float(dynSellFactor)
        dynBuyFactor = float(dynBuyFactor)     
        #-----------------------------Asset manager call--------------------------------------------------------------------------     
        toBuy, S2balanceOK, toSell, S1balanceOK, AvailableS2Assets, AvailableS1Assets = _assetManager(
            strategySettings = strategySettings, 
            BalanceSymbol1 = float(BalanceSymbol1), 
            BalanceSymbol2 = float(BalanceSymbol2), 
            dynFactorBuy = dynBuyFactor, 
            dynFactorSell = dynSellFactor, 
            avarageEntry = avarageEntry, 
            avarageExit = avarageExit, 
            avarageCost = avarageCost, 
            LastPrice = LastPrice
            )
        
        #Remove Numpy stuf
        LastPrice = float(LastPrice)
        maxPrice = float(maxPrice)
        minPrice= float(minPrice)
        toBuy = float(toBuy)
        toSell = float(toSell)

        #Check changes form Max newBuyDropOk
        PercentCahangeFromMax = (maxPrice - LastPrice)/maxPrice * 100
        newBuyDropOk = PercentCahangeFromMax > strategySettings["DipBuy"]
        #Check changes form Min newSellPumpOk
        PercentCahangeFromMin = (LastPrice - minPrice)/minPrice * 100
        newSellPumpOk = PercentCahangeFromMin > strategySettings["TakeProfit"]
        
        #----------------------Cal buy/sel cmds----------------------------
        commission = 0.0 #create a column to bi filled when trade happens
        commission_asset = "NaN"  #create a column to bi filled when trade happens
        if strategySettings["paperTrading"]: #pater trades
            if (newBuyDropOk and
                newTradeEn and
                dynBuyTradeEn and
                S2balanceOK
                ):
                trade = [timestamp_seconds*1000, "Paper", 
                        strategySettings["Symbol1"], 
                        toBuy/LastPrice, 
                        strategySettings["Symbol2"],
                        -toBuy,
                        LastPrice,
                        maxPrice,
                        minPrice,
                        lookBack,
                        avarageCost["avg"],
                        PercentCahangeFromMax,                        
                        commission, 
                        commission_asset
                        ]
                localTradeTables[strategySettings["id"]]["NewData"] = True
                my_tradeData.append(trade)
                localTradeTables[strategySettings["id"]]["PaperTrades"] = my_tradeData
                #TradeSaveTocsv(filePath, trade)
                #Block double trades
                newTradeEn = False
                #Reset saved values
                histStrategyVal[strSaveValMax] = LastPrice
                histStrategyVal[strSaveValMin] = LastPrice
                #logger.info(f"New paper BUY order {trade}")

            if (newSellPumpOk and
                newTradeEn and
                dynSellTradeEn and
                S1balanceOK    
                ):
                trade = [timestamp_seconds*1000, "Paper", 
                        strategySettings["Symbol1"], 
                        -toSell/LastPrice, 
                        strategySettings["Symbol2"],
                        toSell,
                        LastPrice,
                        maxPrice,
                        minPrice,
                        lookBack,
                        avarageCost["avg"],
                        PercentCahangeFromMin,                        
                        commission, 
                        commission_asset
                        ]
                localTradeTables[strategySettings["id"]]["NewData"] = True
                my_tradeData.append(trade)
                localTradeTables[strategySettings["id"]]["PaperTrades"] = my_tradeData
                #TradeSaveTocsv(filePath, trade)
                #Block double trades
                newTradeEn = False
                #Reset saved values
                histStrategyVal[strSaveValMax] = LastPrice
                histStrategyVal[strSaveValMin] = LastPrice
                #logger.info(f"New paper SELL order {trade}")
        else: #-----------------LIVE trades
            if (newBuyDropOk and
                newTradeEn and
                S2balanceOK and
                dynBuyTradeEn                
                ):
                trade = [timestamp_seconds*1000, 
                        "Open",#write order as Open trade manager will close it 
                        strategySettings["Symbol1"],  #2
                        toBuy/LastPrice,          #3
                        strategySettings["Symbol2"],
                        -toBuy,             #5
                        LastPrice,              #6
                        maxPrice,
                        minPrice,
                        lookBack,
                        avarageCost["avg"],            #10
                        PercentCahangeFromMin,  #11                   
                        commission,             #12
                        commission_asset        #13
                        ]
                my_tradeData.append(trade)
                localTradeTables[strategySettings["id"]]["PaperTrades"] = my_tradeData
                #TradeSaveTocsv(filePath, trade)
                #Block double trades
                newTradeEn = False
                #Reset saved values
                histStrategyVal[strSaveValMax] = LastPrice
                histStrategyVal[strSaveValMin] = LastPrice                
                logger.info(f"New BUY order at : {datetime.fromtimestamp(int(timestamp_seconds))} \n "
                            f"strategy id : {strategySettings["id"]} \n "
                            f"pair : {strategySettings["Symbol1"]}/{strategySettings["Symbol2"]} \n "
                            f"BUY : {toBuy/LastPrice} {strategySettings["Symbol1"]} \n "
                            f"for : {toBuy} {strategySettings["Symbol2"]} \n "
                            f"at price : {LastPrice} "
                            )
            if (newSellPumpOk and
                newTradeEn and
                S1balanceOK and
                dynSellTradeEn
                ):
                trade = [timestamp_seconds*1000, "Open", 
                        strategySettings["Symbol1"], 
                        -toSell/LastPrice, 
                        strategySettings["Symbol2"],
                        toSell,
                        LastPrice,
                        maxPrice,
                        minPrice,
                        lookBack,
                        avarageCost["avg"],
                        PercentCahangeFromMin,                        
                        commission, 
                        commission_asset
                        ]
                my_tradeData.append(trade)
                localTradeTables[strategySettings["id"]]["PaperTrades"] = my_tradeData
                #TradeSaveTocsv(filePath, trade)
                #Block double trades
                newTradeEn = False
                #Reset saved values
                histStrategyVal[strSaveValMax] = LastPrice
                histStrategyVal[strSaveValMin] = LastPrice
                logger.info(f"New SELL order at : {datetime.fromtimestamp(int(timestamp_seconds))} \n "
                            f"strategy id : {strategySettings["id"]} \n "
                            f"pair : {strategySettings["Symbol1"]}/{strategySettings["Symbol2"]} \n "
                            f"SELL : {toSell/LastPrice} {strategySettings["Symbol1"]} \n "
                            f"for : {toSell} {strategySettings["Symbol2"]} \n "
                            f"at price : {LastPrice} "
                            )
        
        if True: #Save active strategy values 
            temp = toSell/LastPrice
            countForRound = 2
            while temp < 1 and temp > 0:
                temp = temp*10
                countForRound +=1          
            #Save strategy values 
            activeStrategyData["Last Price"] = LastPrice
            activeStrategyData[f"{strategySettings["Symbol1"]}"] = float(BalanceSymbol1)
            activeStrategyData[f"{strategySettings["Symbol2"]}"] = float(BalanceSymbol2)
            activeStrategyData["Avradge cost"] = round(avarageCost["avg"], strategySettings["roundBuySellorder"])
            activeStrategyData["Avradge entry"] = round(avarageEntry["avg"], strategySettings["roundBuySellorder"])
            activeStrategyData["Avradge exit"] = round(avarageExit["avg"], strategySettings["roundBuySellorder"])
            activeStrategyData["Cost SumS2"] = round(avarageCost["sumS2"], strategySettings["roundBuySellorder"])
            activeStrategyData["Entry SumS2"] = round(avarageEntry["sumS2"], strategySettings["roundBuySellorder"])
            activeStrategyData["Exit SumS2"] = round(avarageExit["sumS2"], strategySettings["roundBuySellorder"])
            activeStrategyData["Cost SumS1"] = round(avarageCost["sumS1"], countForRound)
            activeStrategyData["Entry SumS1"] = round(avarageEntry["sumS1"], countForRound)
            activeStrategyData["Exit SumS1"] = round(avarageExit["sumS1"], countForRound)
            activeStrategyData["Profit_Loss"] = round(totalPnL, strategySettings["roundBuySellorder"])
            activeStrategyData["Profit_LossPercent"] = round(totalPnLpercent, 2)
            activeStrategyData["PnL_realized"] = round(realizedPnL, strategySettings["roundBuySellorder"])
            activeStrategyData["PnL_unrealized"] = round(unrealizedPnL, strategySettings["roundBuySellorder"])
            activeStrategyData["Max Price"] = maxPrice
            activeStrategyData["Min Price"] = minPrice
            activeStrategyData["Buy Ammount"] = toBuy
            activeStrategyData["Buy Factor"] =  round(dynBuyFactor,2) #save active data
            activeStrategyData["Buy Percente change"] = round(PercentCahangeFromMax,2)
            activeStrategyData["Sell Percente change"] = round(PercentCahangeFromMin,2)
            activeStrategyData["Sell Ammount Symbol1"] = round(toSell/LastPrice, countForRound)
            activeStrategyData["Sell Ammount"] = toSell
            activeStrategyData["Sell Factor"] = round(dynSellFactor,2) #save active data

            #Save advanceDCAstatus
            #Get index of the trade strategy
            id = f"id_{strategySettings["id"]}"        
            advanceDCAstatus[id] = {} # initiate / if exist it will be cleared the strategy trade data
            #Fill base data                 
            advanceDCAstatus[id]["Symbol1"] = strategySettings["Symbol1"]
            advanceDCAstatus[id]["Symbol2"] = strategySettings["Symbol2"]
            advanceDCAstatus[id]["BuyBase"] = strategySettings["BuyBase"]
            advanceDCAstatus[id]["BuyMin"] = strategySettings["BuyMin"]
            advanceDCAstatus[id]["SellBase"] = strategySettings["SellBase"]
            advanceDCAstatus[id]["SellMin"] = strategySettings["SellMin"]
            advanceDCAstatus[id]["assetManagerTarget"] = strategySettings["assetManagerTarget"]
            advanceDCAstatus[id]["paperTrading"] = strategySettings["paperTrading"]
            advanceDCAstatus[id]["candleCloseOnly"] = strategySettings["candleCloseOnly"]
            advanceDCAstatus[id]["assetManagerSymbol"] = strategySettings[f"Symbol{strategySettings["assetManagerSymbol"]}"]
            advanceDCAstatus[id]["AvailableS2Assets"] = round(AvailableS2Assets, strategySettings["roundBuySellorder"])
            advanceDCAstatus[id]["AvailableS1Assets"] = round(AvailableS1Assets, countForRound)
            advanceDCAstatus[id]["BalanceSymbol2"] = round(float(BalanceSymbol2), strategySettings["roundBuySellorder"])
            advanceDCAstatus[id]["BalanceSymbol1"] = round(float(BalanceSymbol1), countForRound)
            advanceDCAstatus[id]["CandleInterval"] = strategySettings["CandleInterval"]
            advanceDCAstatus[id]["newTradeEn"] = newTradeEn
            advanceDCAstatus[id]["newBuyDropOk"] = newBuyDropOk
            advanceDCAstatus[id]["dynBuyTradeEn"] = dynBuyTradeEn
            advanceDCAstatus[id]["newBuyBalanceOk"] = S2balanceOK
            advanceDCAstatus[id]["MinWeight_Buy"] = strategySettings[f"MinWeight_Buy"]
            advanceDCAstatus[id]["newSellPumpOk"] = newSellPumpOk
            advanceDCAstatus[id]["newSellBalanceOk"] = S1balanceOK
            advanceDCAstatus[id]["dynSellTradeEn"] = dynSellTradeEn
            advanceDCAstatus[id]["MinWeight_Sell"] = strategySettings[f"MinWeight_Sell"]
            advanceDCAstatus[id]["type"] = strategySettings["type"]
            advanceDCAstatus[id]["name"] = f"{strategySettings["name"]} ID:{strategySettings["id"]} {strategySettings["Symbol1"]}/{strategySettings["Symbol2"]}"
            advanceDCAstatus[id]["data"] = activeStrategyData

        #print(f"Strategy status data: {advanceDCAstatus}")  
        # Wrtite status to logger 
        logger.debug(f"Strategy id {strategySettings["id"]} \n {strategySettings["name"]} on {strategySettings["Symbol1"]}/{strategySettings["Symbol2"]} pair \n"
                    f"last price: {LastPrice}; \n Avrage cost: {avarageCost["avg"]}; \n Profit/Loss : {round(totalPnL,6)} | {round(totalPnLpercent,2)} %; \n Lookback val: {lookBack}"
                    )        
        return
    except Exception as e:
        logger.error(f"_advanceDCA() error: {e}")


#Load historical data from file to variable historyKlineData
def _manageHistKlineData(strategySettings, klineData = None, Symbol1="", Symbol2="", Interval=""):  
    global historyKlineData
    if klineData == None: #Build all from files
        pairIntervals, _ = _generateListOfPairsAndIntervals(strategySettings)
        #Clear the whole list
        historyKlineData.clear()
        for Pair in list(pairIntervals.keys()): #run trough all the stratagies
            #Creat a dicionary structure for each pair and candle interval
            #Pair = f"{strategy["Symbol1"]}{strategy["Symbol2"]}" 
            if not Pair in historyKlineData:
                historyKlineData[Pair] = {
                    "Symbol1" : pairIntervals[Pair]["Symbol1"],
                    "Symbol2" : pairIntervals[Pair]["Symbol2"],
                    "Intervals" : {                        
                    }
                }
            for interval in pairIntervals[Pair]["Intervals"]:
                filePath = f"data/_{pairIntervals[Pair]["Symbol1"]}_{pairIntervals[Pair]["Symbol2"]}_candle_{interval}.csv"                
                historyKlineData[Pair]["Intervals"][interval] = None
                if os.path.exists(filePath):
                    my_histData = np.genfromtxt(filePath, delimiter=",") #Create an array from csv
                    historyKlineData[Pair]["Intervals"][interval] = {
                        "timeStampOpen": my_histData[:,KLINE_TABLE_COL_TIMESTAMP_OPEN],
                        "timeStampClose": my_histData[:,KLINE_TABLE_COL_TIMESTAMP_CLOSE],
                        "open": my_histData[:,KLINE_TABLE_COL_OPEN],
                        "close": my_histData[:,KLINE_TABLE_COL_CLOSE],
                        "high": my_histData[:,KLINE_TABLE_COL_HIGH],
                        "low": my_histData[:,KLINE_TABLE_COL_LOW],
                        "vol1": my_histData[:,KLINE_TABLE_COL_VOLUME_S1]
                    } #Create an array from csv
                else:
                    logger.info(f"loadHistKlineData() error: missing hist file: {filePath}")

    else: #update one that was passed
        Pair = f"{Symbol1}{Symbol2}" 
        if not Pair in historyKlineData:
                historyKlineData[Pair] = {
                    "Symbol1" : Symbol1,
                    "Symbol2" : Symbol2,
                    "Intervals" : {
                        Interval : None
                    }
                }
        numPyData = np.array(klineData,dtype=np.float64)
        historyKlineData[Pair]["Intervals"][Interval] = {
                            "timeStampOpen": numPyData[:,KLINE_TABLE_COL_TIMESTAMP_OPEN],
                            "timeStampClose": numPyData[:,KLINE_TABLE_COL_TIMESTAMP_CLOSE],
                            "open": numPyData[:,KLINE_TABLE_COL_OPEN],
                            "close": numPyData[:,KLINE_TABLE_COL_CLOSE],
                            "high": numPyData[:,KLINE_TABLE_COL_HIGH],
                            "low": numPyData[:,KLINE_TABLE_COL_LOW],
                            "vol1": numPyData[:,KLINE_TABLE_COL_VOLUME_S1]
                        } 
        #Write data to file
        csvFile = open(f"data/_{Symbol1}_{Symbol2}_candle_{Interval}.csv", "w", newline='')  #Open a Csv File
        csvFile_writer = csv.writer(csvFile, delimiter="," ) #set csv delimiter for writer

        for candlestick in klineData: #Go trough rows
            csvFile_writer.writerow(candlestick) # Write rows

        csvFile.close() # close ed csv file

#Check candles hist data aging
def _timeCheckHisKlineData(timestamp_seconds):
    AllDataUpToDate = True
    for Pair in list(historyKlineData.keys()):
        for interval in list(historyKlineData[Pair]["Intervals"].keys()):
            timestamp_close = int(historyKlineData[Pair]["Intervals"][interval]["timeStampClose"][-1]/1000)
            if (timestamp_close < timestamp_seconds) : #Check if now() is bigger than timestamp of close the data is old new candles needed
                AllDataUpToDate= False
    return AllDataUpToDate

#Update last candle of historyKlineData from klinStreamdData
def _updateLastCandle_HistKlineData(Pair):
    global historyKlineData
    close = klinStreamdData[Pair]["close"] #Use only close value to update low and hig if necesary than the stream interval is irelevant
    for histInterval in list(historyKlineData[Pair]["Intervals"].keys()): #go trough different intervals 
        lastDatahigh = historyKlineData[Pair]["Intervals"][histInterval]["high"][-1]
        lastDatalow = historyKlineData[Pair]["Intervals"][histInterval]["low"][-1]
        lastDatahigh = max(lastDatahigh, close)
        lastDatalow = min(lastDatalow, close)
        historyKlineData[Pair]["Intervals"][histInterval]["close"][-1] = close
        historyKlineData[Pair]["Intervals"][histInterval]["high"][-1] = lastDatahigh
        historyKlineData[Pair]["Intervals"][histInterval]["low"][-1] = lastDatalow

#Function to create a list of all pairs and their intervals with including the ones of indicators
def _generateListOfPairsAndIntervals(strategySettings):
    pairIntervals = {}
    AllFilesExists = True
    for strategy in strategySettings: #run trough all the stratagies
        #Creat a dicionary structure for each pair and candle interval
        Pair = f"{strategy["Symbol1"]}{strategy["Symbol2"]}" 
        if not Pair in pairIntervals: #If unique add
            pairIntervals[Pair] = {
                "Symbol1" : strategy["Symbol1"],
                "Symbol2" : strategy["Symbol2"],
                "Intervals" : [strategy["CandleInterval"]]
            }
        if not strategy["CandleInterval"] in pairIntervals[Pair]["Intervals"]:#Check if unique
            pairIntervals[Pair]["Intervals"].append(strategy["CandleInterval"]) #Add to the list of intervals
        filePath = f"data/_{strategy["Symbol1"]}_{strategy["Symbol2"]}_candle_{strategy["CandleInterval"]}.csv"            
        if not os.path.exists(filePath):                
            AllFilesExists = False
        for key in strategy.keys(): #Go trough all keys to find DynamicBuy and Sell
            if "Dynamic" in key: #check if it is the list of indicators
                for ind in strategy[key]: #go trough the list
                    interval = ind.get("Interval") #Get if exists else it will be None value
                    if not interval in pairIntervals[Pair]["Intervals"] and interval != None and interval in INDICATOR_INTERVAL_LIST: #Check if unique
                        pairIntervals[Pair]["Intervals"].append(interval) #Add to the list of intervals
                        filePath = f"data/_{strategy["Symbol1"]}_{strategy["Symbol2"]}_candle_{interval}.csv"            
                        if not os.path.exists(filePath):                
                            AllFilesExists = False
    return pairIntervals, AllFilesExists

def _readTradeCsv(filePath):    
    rows = []
    if os.path.exists(filePath):
        csvFile = open(filePath,"r", newline="", encoding="utf-8")
        reader = csv.reader(csvFile, delimiter=",")
        for row in reader:
            formatRow = [int(row[TRADE_TABLE_COL_TIMESTAMP]), #Format the rows as they are all strings from the reader
                str(row[TRADE_TABLE_COL_ID]),
                str(row[TRADE_TABLE_COL_SYMBOL_1]),
                float(row[TRADE_TABLE_COL_ASSET_S1_QT]),
                str(row[TRADE_TABLE_COL_SYMBOL_2]),
                float(row[TRADE_TABLE_COL_ASSET_S2_QT]),
                float(row[TRADE_TABLE_COL_PRICE]),
                float(row[TRADE_TABLE_COL_MAX]),
                float(row[TRADE_TABLE_COL_MIN]),
                int(row[TRADE_TABLE_COL_LOOKBACK]),
                float(row[TRADE_TABLE_COL_AVG_COST]),
                float(row[TRADE_TABLE_COL_CHANGE]),
                float(row[TRADE_TABLE_COL_COMMISION]),
                str(row[TRADE_TABLE_COL_COMMISION_ASSET])]
            rows.append(formatRow)
        csvFile.close()
        return rows
    
def _tradeTableManagment(strategySettings):
    global localTradeTables
    try:
        #get current time data
        now_utc = datetime.now(timezone.utc)
        timestamp_seconds = int(now_utc.timestamp())
        basicSettings = loadBsettings()
        timeLimitopenOrder = basicSettings["liveTradeAging"]
        tempIDList = []
        for strategy in strategySettings: #for loop to troug all strategies
            Pair = f"{strategy["Symbol1"]}{strategy["Symbol2"]}"
            filePathBase = (f"Trade_{strategy["type"]}_"
                        f"{strategy["Symbol1"]}_{strategy["Symbol2"]}_"
                        f"{strategy["id"]}_.csv")
            filePathPaper = f"data/_Paper{filePathBase}" 
            filePathLive = f"data/_{filePathBase}"
            tempIDList.append(strategy["id"]) #Add ti Id list to check for old strategies
            if not strategy["id"] in localTradeTables: #creat new data inserts 
                localTradeTables[strategy["id"]] = {
                    "Pair" : Pair,
                    "FilePathBase" : filePathBase,
                    "Type" : strategy["type"],
                    "Symbol1" : strategy["Symbol1"],
                    "Symbol2" : strategy["Symbol2"],
                    "NewData" : False,
                    "PaperTrading" : strategy["paperTrading"],
                    "CandleInterval" : strategy["CandleInterval"],
                    "type" : strategy["type"],
                    "name" : strategy["name"],
                    "PaperTrades" : None,
                    "Trades" : None
                }
                #Initial load of data from .csv           
                localTradeTables[strategy["id"]]["PaperTrades"] = _readTradeCsv(filePathPaper)
                localTradeTables[strategy["id"]]["Trades"] = _readTradeCsv(filePathLive)

            else: #check existing data
                if Pair != localTradeTables[strategy["id"]]["Pair"]: #check if Pair changed remove trading tables and relod from file if exists
                    localTradeTables[strategy["id"]]["PaperTrades"] = None
                    localTradeTables[strategy["id"]]["Trades"] = None                    
                    #Initial load of data from .csv
                    localTradeTables[strategy["id"]]["PaperTrades"] = _readTradeCsv(filePathPaper)
                    localTradeTables[strategy["id"]]["Trades"] = _readTradeCsv(filePathLive)
                if not os.path.exists(filePathPaper) and not localTradeTables[strategy["id"]]["NewData"]: #If no table clear the local data (when reset from manager)
                    localTradeTables[strategy["id"]]["PaperTrades"] = None
                if not os.path.exists(filePathLive) and not localTradeTables[strategy["id"]]["NewData"]: #If no table clear the local data (when reset from manager)
                    localTradeTables[strategy["id"]]["Trades"] = None
                localTradeTables[strategy["id"]]["Pair"] = Pair
                localTradeTables[strategy["id"]]["FilePathBase"] = filePathBase
                localTradeTables[strategy["id"]]["Symbol1"] = strategy["Symbol1"]
                localTradeTables[strategy["id"]]["Symbol2"] = strategy["Symbol2"]
                localTradeTables[strategy["id"]]["PaperTrading"] = strategy["paperTrading"]
                localTradeTables[strategy["id"]]["CandleInterval"] = strategy["CandleInterval"]
                localTradeTables[strategy["id"]]["type"] = strategy["type"]
                localTradeTables[strategy["id"]]["name"] = strategy["name"]

        for idKey in list(localTradeTables.keys()):#Run trough to manage changes
            if idKey in tempIDList:# delete if the strategy does not exist anymore
                if not localTradeTables[idKey]["PaperTrading"]: #if LIVE go trough the table to find open orders and execute them
                    #Delete old open trandes
                    tradeTable = localTradeTables[idKey]["Trades"]
                    tradeTableNew = [ #Filter out all open trades 
                        trade for trade in tradeTable
                        if trade[TRADE_TABLE_COL_ID] != "Open" 
                        ]
                    openOreders = [ #Filter new open orders
                        trade for trade in tradeTable
                        if trade[TRADE_TABLE_COL_ID] == "Open" and (timestamp_seconds - int(trade[TRADE_TABLE_COL_TIMESTAMP])/1000 ) < timeLimitopenOrder
                        ]
                    if len(openOreders): #If any open orders execute the last one only
                        tradeResponse = sendTrade(openOreders[-1])
                        if tradeResponse != None:# If succesful append trade
                            tradeTableNew.append(tradeResponse) #Add to new table
                            localTradeTables[idKey]["NewData"] = True # Mark for updating the .csv
                    localTradeTables[idKey]["Trades"] = None#Empty before inserting the updated one
                    localTradeTables[idKey]["Trades"] = tradeTableNew
            
                #Update data in .csv
                if localTradeTables[idKey]["NewData"]:
                    if localTradeTables[idKey]["PaperTrading"]: #Create path and table for saving 
                        filePath = f"data/_Paper{localTradeTables[idKey]["FilePathBase"]}"
                        tradeTabelToSave = localTradeTables[idKey]["PaperTrades"]
                    else:                    
                        filePath = f"data/_{localTradeTables[idKey]["FilePathBase"]}"
                        tradeTabelToSave = localTradeTables[idKey]["Trades"]
                    #Write to .csv overwrite everithing 
                    with open(filePath,mode="w", newline="", encoding="utf-8") as csvFile:
                        writer = csv.writer(csvFile, delimiter=",")                        
                        writer.writerows(tradeTabelToSave)
                    csvFile.close()
                    localTradeTables[idKey]["NewData"] = False
                        
            else: #Delete entry of an old strategy
                del localTradeTables[idKey]
        
        _creatTradeTablesView()

    except Exception as e:
        logger.error(f"tradeTableManagment() error: {e}")

#History cleanup -> delete data not used in any of the stratagies (preventing accesing old data in case of reuse strategy)
def _clearUnusedHistData(strategySettings):
    try:
        idList = []
        filePathList = []
        pairIntervals, AllFilesExists = _generateListOfPairsAndIntervals(strategySettings)
        # Call All stratagies         
        for strategy in strategySettings: #run trough all the stratagies            
            if str.lower(strategy["type"]) == str.lower("AdvancedDCA"): #run AdvancedDCA strategy only
                id = strategy["id"]                
                Pair = f"{strategy["Symbol1"]}{strategy["Symbol2"]}"
                idList.append(f"{strategy["type"]}_{id}_{Pair}_min")
                idList.append(f"{strategy["type"]}_{id}_{Pair}_max")
                
        for Pair in pairIntervals:
            for interval in pairIntervals[Pair]["Intervals"]:
                #path to candlestick history without data
                filePath = f"_{pairIntervals[Pair]["Symbol1"]}_{pairIntervals[Pair]["Symbol2"]}_candle_{interval}.csv"
                filePathList.append(filePath)

        entries = os.listdir("data") # get all file names in directory
        for entry in entries:
            if "_candle_" in entry and not entry in filePathList:
                os.remove(f"data/{entry}") #remove file
        #Clear history values of strategy not in use
        for key in list(histStrategyVal.keys()):
            if not key in idList:
                del histStrategyVal[key]

    except Exception as e: 
        logger.error(f"_clearUnusedHistData error: {e}")


listOldPrices = {}
#Call the strategies -------------------------------------------------------------------------------------------
def strategyRun():
    global listOldPrices, timeHistFetch
    try:         
        basicSettings = loadBsettings()
        strategySettings = loadStrSettings()       
        #get current time data
        now_utc = datetime.now(timezone.utc)
        timestamp_seconds = int(now_utc.timestamp())
        #Call cleenup
        _clearUnusedHistData(strategySettings)
        advanceDCAstatus.clear()
        _gefFearAndGread() #get Fear and Gread index
        #Check if historical data exists if not reset historical time fetch (when new stratagy is added the data needs to be requested)
        pairIntervals, AllFilesExists = _generateListOfPairsAndIntervals(strategySettings) 
        #Check His data times need to be updated
        AllDataUpToDate = _timeCheckHisKlineData(timestamp_seconds)
        if not AllFilesExists or not AllDataUpToDate:  #force hist data fetch            
            timeHistFetch = 0

        # Fetch history data
        if (timeHistFetch < (timestamp_seconds - (basicSettings["histDataUpdate"] *60)) or timeHistFetch == 0):
            logger.debug(f"Fetching historical data")            
            timeHistFetch = timestamp_seconds # reset Timer  
            #Fetch historical data for all pairs and needed intervals
            for Pair in pairIntervals:
                for interval in pairIntervals[Pair]["Intervals"]:
                    #call function 
                    klineData = fetch_histData(
                        Symbol1=pairIntervals[Pair]["Symbol1"],
                        Symbol2=pairIntervals[Pair]["Symbol2"],
                        Interval=interval,
                        numData=basicSettings["numOfHisCandles"]                                         
                        )   
                    #Save to local data
                    if klineData !=None:
                        _manageHistKlineData(
                            strategySettings, 
                            klineData, 
                            Symbol1=pairIntervals[Pair]["Symbol1"], 
                            Symbol2=pairIntervals[Pair]["Symbol2"], 
                            Interval=interval) #Update local variable with recived data  
            #Read user data
            fetch_userData() 
            #src.loadHistKlineData(strategySettings) #read from .csv files and store in local table

        # Call All stratagies         
        for strategy in strategySettings: #run trough all the stratagies
            if str.lower(strategy["type"]) == str.lower("AdvancedDCA"): #run AdvancedDCA strategy only
                balanceS1 = 0
                balanceS2 = 0              
                Pair = f"{strategy["Symbol1"]}{strategy["Symbol2"]}"
                
                if strategy["Symbol1"] in my_balances:
                    balanceS1 = my_balances[strategy["Symbol1"]]["Available"]
                if strategy["Symbol2"] in my_balances:
                    balanceS2 = my_balances[strategy["Symbol2"]]["Available"] 
                #Set last price -1 will make strategy use data from history
                lastPrice = -1.0
                if len(klinStreamdData) > 0: #check if ther is any data from stream
                    if Pair in klinStreamdData.keys(): #Check if the pair exists
                        if (timestamp_seconds - klinStreamdData[Pair]["Time"]) < 180: #check the data is not older than 3 min
                            lastPrice = klinStreamdData[Pair]["close"] #get close price
                            _updateLastCandle_HistKlineData(Pair)
                            #Call Strategy function only if there is stream data
                            _advanceDCA(strategy, balanceS1, balanceS2, lastPrice)
                        else:
                            if not Pair in listOldPrices: #Try not to spam logger
                                logger.error(f"strategyRun() error: Old price data for {Pair} {datetime.fromtimestamp(int(klinStreamdData[Pair]["Time"]))}")
                            else:                                
                                if listOldPrices[Pair] != klinStreamdData[Pair]["Time"]:
                                    logger.error(f"strategyRun() error: Old price data for {Pair} {datetime.fromtimestamp(int(klinStreamdData[Pair]["Time"]))}")                                    
                            listOldPrices[Pair] = klinStreamdData[Pair]["Time"]
                    else:
                        logger.error(f"strategyRun() error: No price data for {Pair} ")
                else:
                    logger.error(f"strategyRun() error: No price data for ALL")
            
        _tradeTableManagment(strategySettings)
        #save_histStrategyVal()

    except Exception as e: 
        logger.error(f"strategyRun() error: {e}")

def shutDown():
    _save_histStrategyVal()

def init():
    strategy_settings = loadStrSettings()
    #Run first to fill local variables
    _load_histStrategyVal()
    _gefFearAndGread() 
    _tradeTableManagment(strategy_settings)
    _manageHistKlineData(strategy_settings)

init()