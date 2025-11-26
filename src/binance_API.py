from .settings import loadBsettings, loadStrSettings
from .constants import(
    LOG_PATH_BINANCE_API,
    FILE_PATH_EXCHANGE_INFO,
    FILE_PATH_USER_DATA_CSV,
    FILE_PATH_USER_DATA_JSON,
    INTERVAL_LIST,
    TRADE_TABLE_COL_TIMESTAMP,
    TRADE_TABLE_COL_ID,
    TRADE_TABLE_COL_SYMBOL_1,
    TRADE_TABLE_COL_ASSET_S1_QT,
    TRADE_TABLE_COL_SYMBOL_2,
    TRADE_TABLE_COL_ASSET_S2_QT,
    TRADE_TABLE_COL_PRICE,
    TRADE_TABLE_COL_COMMISION,
    TRADE_TABLE_COL_COMMISION_ASSET
)

import threading
import logging
import asyncio
import os
import csv
import json
from datetime import datetime, timezone

from binance_sdk_spot.spot import (
    Spot,
    SPOT_WS_STREAMS_PROD_URL,
    ConfigurationWebSocketAPI,
    ConfigurationWebSocketStreams
    )
from binance_common.constants import WebsocketMode
from binance_sdk_spot.websocket_api.models import KlinesIntervalEnum,ExchangeInfoSymbolStatusEnum
from binance_sdk_spot.websocket_streams.models import KlineIntervalEnum
from telegram import Bot

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_BINANCE_API)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

basicSettings = loadBsettings()

my_balances = {}
#Threding variables for Websocet
exchange_info_data = {}
lock_websocetCmds = threading.Lock()
event_websocetCmd = threading.Event()
websocetCmds={ #Used for communicating between Websocet_API thread and main thread
    "cmd": "done", #ping, history, trade, userData
    "data" : {},
    "return" : "", #Data that will be returned to not brake while loop
    "connected" : False,
    "TelegramMsg" : ""
}
#Threding variables for Stream
streamCmds={ #Used for communicating between stream_API thread and main thread
    "cmd": "done", #ping, history, trade, userData
    "data" : {},
    "return" : "", #Data that will be returned to not brake while loop
    "connected" : False
}
klinStreamdData = {} #Data from streams for last price,...
activStreamList = {}

#Send telegram message
async def _telegramSend(text):
    try:
        telegram_token, telegram_chatID = _getTelegramTOKEN()
        bot = Bot(token=telegram_token       
        )
        await bot.send_message(chat_id=telegram_chatID, text=text)
    except Exception as e:
        logger.error(f"telegramSend() error: {e}")

#Get Telegram TOKEN and chatID from file or enviroment
def _getTelegramTOKEN():
    try:
        #Get keys from inviroment if not defined
        if "telegram_TOKEN" in basicSettings["telegram_TOKEN"]:
            telegram_token = os.environ.get("TELEGRAM_TOKEN")
        else:
            telegram_token = basicSettings["telegram_TOKEN"]
        if "telegram_chatID" in basicSettings["telegram_chatID"]:
            telegram_chatID = os.environ.get("TELEGRAM_CHATID")
        else:
            telegram_chatID = basicSettings["telegram_chatID"]
        return telegram_token, telegram_chatID
    except Exception as e:
        logger.error(f"_getTelegramTOKEN() error: {e}")

#Get Binance API key and secret from file or enviroment
def _getAPI():
    try:
        #Get keys from inviroment if not defined
        if "API_KEY" in basicSettings["API_KEY"]:
            api_key = os.environ.get("BINANCE_API_KEY")
        else:
            api_key = basicSettings["API_KEY"]
        if "API_SECRET" in basicSettings["API_SECRET"]:
            api_secret = os.environ.get("BINANCE_API_SECRET")
        else:
            api_secret = basicSettings["API_SECRET"]
        return api_key, api_secret
    except Exception as e:
        logger.error(f"getAPI() error: {e}")

#Disconnect both by sending cmd to the threads
def disconnectAPI(stream = True, Websocet = True):
    print("Disconnecting from API")
    if stream:
        streamCmds["cmd"] = "disconnect"        
    if Websocet:
        with lock_websocetCmds: #Locking the change to websocetCmds
            websocetCmds["cmd"] = "disconnect"

#------------------------------STREAM connection loop------------------------------------
async def klineStream(loopRuntime = 5, maxNoData = 10, initialIntervalIndex = 1):
    global activStreamList, streamCmds
    connectionStream = None    
    # Create configuration for the WebSocket Streams
    configuration_ws_streams = ConfigurationWebSocketStreams(
        stream_url=os.getenv("STREAM_URL", SPOT_WS_STREAMS_PROD_URL),
        reconnect_delay=basicSettings["reconnect_delay"],
        mode= WebsocketMode.SINGLE,
        pool_size=1 #If more tha 1 there are problems with reconnectiong because it does not close the task
        )
    logger.info(f"kLineStream() connection configuration: stream_url={configuration_ws_streams.stream_url},"
                f" reconnect_delay={configuration_ws_streams.reconnect_delay}, "
                f" unit={configuration_ws_streams.time_unit}, "
                f" mode={configuration_ws_streams.mode}, "
                f" pool_size={configuration_ws_streams.pool_size}, "
                f" https_agent={configuration_ws_streams.https_agent}, "
                )   
 
    logger.info("kLineStream() Starts the event loop")     
    timeUpdates = [] #Local data for saving in a loop
    stremLastData = {}
    
    intervalIndex = initialIntervalIndex % len(INTERVAL_LIST) #Devides input index with lenght of list and returns what is left 4%6 = 2
    interval = INTERVAL_LIST[intervalIndex]
    errorCount = 0

    try:
        # Initialize Spot client has to be here for reconection purpouse
        clientStream = Spot(config_ws_streams=configuration_ws_streams)
        #Connect
        connectionStream = await clientStream.websocket_streams.create_connection()
        countNoData = 0
        timePing = int(datetime.now(timezone.utc).timestamp())
        timeDataCheck = timePing
        activStreamList.clear()    #list of subscribed streams
        firstRun = True  
        dataError = False    
        while True:  
            streamCmds["connected"] =True
            #Get time
            now_utc = datetime.now(timezone.utc)
            timestamp_seconds = int(now_utc.timestamp())              
            #create a list of requested streams depending of settings
            strategySettings = loadStrSettings() #Load setrategy settings
            requestedStreamList = {} 
            for Strategy in strategySettings: #run trough all the stratagies
                Pair = f"{Strategy["Symbol1"]}{Strategy["Symbol2"]}"
                if Pair not in requestedStreamList: #add only if unique
                    requestedStreamList[Pair] = interval #all streams will be 15min do not se the neeed to change this
            #Subscribe to requested streams if not subscribed
            for Pair in requestedStreamList:                
                if not Pair in activStreamList: #If not in active stream list start a stream and add to the list   
                    stream = None
                    stream = await connectionStream.kline( 
                        symbol=Pair,
                        interval=KlineIntervalEnum[f"INTERVAL_{interval}"].value,
                    ) 
                    stream.on("message", lambda data: _saveStreamdata(data)) 
                    activStreamList[Pair] = requestedStreamList[Pair]
                    logger.info(f"kLineStream() Subscribe to stream for: {Pair} with interval = {requestedStreamList[Pair]}")
                    del stream
            

            #Connection data integrity monitoring --------------------------------------------
            if (timestamp_seconds - timeDataCheck) >= 15 and not firstRun: #check data every 15s     
                timeDataCheck = timestamp_seconds
                #compute if streams are receiving new data
                timeUpdates = [] 
                if len(klinStreamdData):                               
                    for key in klinStreamdData:
                        if key in stremLastData.keys(): 
                            timeUpdates.append(klinStreamdData[key]["Time"] - stremLastData[key]["Time"]) #Subtract time if no connection the values should be all 0
                if len(timeUpdates) and len(activStreamList) == len(requestedStreamList):
                    maxTime= max(timeUpdates)
                    if maxTime == 0:
                        countNoData +=1
                    else:
                        countNoData =0 
                stremLastData = klinStreamdData.copy()
                #Handel NO DATA error--------------------------------------------
                if countNoData >0:
                    logger.warning(f"kLineStream() No data recived from stream {countNoData}")
                    timePing = 0 #Requestr ping -> list_subscribe
                if countNoData > maxNoData: #Generate logger message before unsubscribing from streams
                    logger.error(f"kLineStream(): No data recived from stream {countNoData} > {maxNoData}! ")
                    print(f"kLineStream() No data recived from stream {countNoData} > {maxNoData}! ")
                    #Set data error for procesing down the line
                    dataError = True                
                    countNoData = 0             
            
            # Periodically verify server-side subscription list to detect mismatch
            if (timestamp_seconds - timePing) > int(basicSettings["pingUpdate"] *60) and not firstRun : # check time last ping
                timePing = timestamp_seconds
                try:
                    allSubs = await connectionStream.list_subscribe()
                    if len(activStreamList) > len(allSubs["result"]): #Error mismatch streams this happens when reconnection is needed
                        logger.warning(f"kLineStream() streams tracker error: server= {allSubs["result"]} | local= {activStreamList}")
                        dataError = True
                    # rebuild activStreamList from server response
                    activStreamList.clear()
                    for sub in allSubs["result"]:    # update active stream list  
                        strFormated, _, _  = sub.partition("@") 
                        activStreamList[str.upper(strFormated)] = interval
                    #print(f"kLineStream() subscribed streams: {allSubs}")
                except Exception as e:
                    logger.error(f"kLineStream() list_subscribe() conection error: {e}")
                    errorCount +=1 #Count errors for disconnect

            
            # New intervals if no data on old ones
            if dataError: #Error detected
                #break #will disconnect
                intervalIndex = (intervalIndex + 1) % len(INTERVAL_LIST)
                interval = INTERVAL_LIST[intervalIndex] #changing the stream to a different time periond fixes it because new stream subscribtion works 
                dataError = False
            #------------------------------------------------------------------------------------------------           

            if streamCmds["cmd"] == "disconnect": #Disconnecting
                requestedStreamList.clear() #this will unsubscribe from all
            #Unsubscribing logic------------------------------------------------------
            for Pair in list(activStreamList.keys()):
                if not Pair in requestedStreamList:
                    try:
                        #Remove from stream
                        logger.info(f"kLineStream() Unsubscribe from stream for: {Pair} with interval = {activStreamList[Pair]}")
                        strFormat = f"{str.lower(Pair)}@kline_{activStreamList[Pair]}"
                        await connectionStream.unsubscribe(streams=strFormat)
                        del activStreamList[Pair]  #Delete active stream list
                    except Exception as e:
                        logger.error(f"kLineStream() unsubscribe error: {e}")
                        errorCount +=1 #Count errors for disconnect

            firstRun = False
            if errorCount > 2: #if errors excede X start reconnect
                logger.error(f"kLineStream() Connection error count: {errorCount}")
                break #Disconnect

            if streamCmds["cmd"] == "disconnect": #Disconnecting
                break #exit while loop
            await asyncio.sleep(loopRuntime)
    except Exception as e:
        logger.error(f"kLineStream() Connection lost or error: {e}")
        if basicSettings["useTelegram"]: #Write telegram message
            telegramMsg = f"kLineStream() Connection lost or error: {e}"
            await asyncio.wait_for(_telegramSend(telegramMsg), timeout=5)#Send telegram msg 

    finally:
        streamCmds["connected"] =False
    try:
        if connectionStream:
            await asyncio.wait_for(connectionStream.close_connection(close_session=True), timeout=10)
    except Exception as e:
        logger.error(f"kLineStream(): close connection error: {e}")
    try:
        if clientStream:
            # if the SDK has a cleanup method, call it (some SDKs provide close_connections())
            if hasattr(clientStream, "close_connections"):
                await asyncio.sleep(0)   # yield to event loop
                await asyncio.wait_for(clientStream.close_connections(), timeout=10)        
    except Exception as e:
        logger.error(f"kLineStream(): close client error: {e}")
    
    # Cancel lingering tasks in this event loop to avoid "task destroyed but pending"
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        logger.warning(f"kLineStream(): cancelling {len(pending)} pending tasks")
        for t in pending:
            try:
                t.cancel()
            except Exception:
                pass
        await asyncio.gather(*pending, return_exceptions=True)
    
    del clientStream

#Function for catching stream data
def _saveStreamdata(data):
    try:
        global klinStreamdData
        #print(f"Stream data recived for: {data.s}")
        if data:
            klinStreamdData[data.s] = {
                "Time" : int(data.E/1000),
                "open" : float(data.k.o),
                "close" : float(data.k.c),
                "high": float(data.k.h),
                "low": float(data.k.l),
                "volume": float(data.k.v),
                "interval" : data.k.i
            }    
    except Exception as e:
        logger.error(f"Save Stream data() error: {e}")

#----------------------------WEBSOCET connection loop-----------------
async def websocetManage(loopRuntime = 1):      
    logger.info("websocetManage() Starts the event loop")    
    global websocetCmds
    connection = None
    errorCount=0
    api_key, api_secret = _getAPI()
    # Create configuration for the WebSocket API
    configuration_ws_api = ConfigurationWebSocketAPI(
        api_key = api_key,
        api_secret = api_secret,
        timeout= basicSettings["timeout"],
        reconnect_delay=basicSettings["reconnect_delay"],
        mode= WebsocketMode.SINGLE,
        pool_size=1
        )
    logger.info(f"websocetManage() connection configuration: timeout={configuration_ws_api.timeout},"
                f" reconnect_delay={configuration_ws_api.reconnect_delay}, "
                f" stream_url={configuration_ws_api.stream_url}, "
                f" unit={configuration_ws_api.time_unit}, "
                f" mode={configuration_ws_api.mode}, "
                f" pool_size={configuration_ws_api.pool_size}, "
                f" https_agent={configuration_ws_api.https_agent}, "
                )
    try:         #Local data for saving in a loop
        # Initialize Spot client
        client = Spot(config_ws_api=configuration_ws_api)
        # Establish connection to API
        if connection == None:
            connection = await client.websocket_api.create_connection() # connect to binance
        if basicSettings["useTelegram"]:
            await asyncio.wait_for(_telegramSend("Bot connected to API"), timeout=10)

        firstRun = True 
        while True:      
            websocetCmds["connected"] = True  
            if not firstRun:
                event_websocetCmd.clear()
                await asyncio.sleep(loopRuntime)
            
            if websocetCmds["cmd"] != "done":
                with lock_websocetCmds: #Locking the change to websocetCmds
                    websocetCmds["return"] = "return" #write return in case no data
                    match websocetCmds["cmd"]: #Sending requests to API
                        case "disconnect":    
                            break
                        case "exchange_info":
                            try:
                                response = await connection.exchange_info(#symbols= ["BTCUSDC", "ETHUSDC", "DSEFS"],
                                    permissions="SPOT",
                                    symbol_status = ExchangeInfoSymbolStatusEnum.TRADING,
                                    show_permission_sets=False
                                    )
                                responseBigData = response.data().result.symbols
                                responseList = {}
                                for obj in responseBigData:
                                    responseList[obj.symbol]={}
                                    responseList[obj.symbol]["base_asset_precision"] = obj.base_asset_precision
                                    responseList[obj.symbol]["quote_asset_precision"] = obj.quote_asset_precision
                                    responseList[obj.symbol]["quote_precision"] = obj.quote_precision
                                    for filter in obj.filters:
                                        if filter.filter_type == 'LOT_SIZE':
                                            responseList[obj.symbol]["step_size"] = float(filter.step_size)
                                            responseList[obj.symbol]["min_qty"] = float(filter.min_qty)
                                            responseList[obj.symbol]["max_qty"] = float(filter.max_qty)
                                            temp = float(filter.step_size)
                                            order_precision =0
                                            while temp < 1.0 and temp !=0:
                                                temp *= 10
                                                order_precision +=1
                                            responseList[obj.symbol]["order_precision"] = order_precision
                                websocetCmds["return"] = responseList
                                logger.info(f"exchange_info() asset list recived")
                            except Exception as e:
                                logger.error(f"websocetManage() Connection error: exchange_info() {e}")
                                websocetCmds["return"] = "error"
                                errorCount +=1  
                        case "ping": #Ping client    
                            try:                    
                                response = await connection.ping()
                                rate_limits = response.rate_limits
                                responseData = response.data()
                                logger.debug(f"ping() rate limits: {rate_limits}")    
                                websocetCmds["return"] = responseData
                            except Exception as e:
                                logger.error(f"websocetManage() Connection error: ping() {e}")
                                websocetCmds["return"] = "error"
                                errorCount +=1                 
                        case "history": #Retrive history
                            try:
                                response = await connection.klines(
                                    symbol= websocetCmds["data"]["symbol"],
                                    interval= websocetCmds["data"]["interval"],
                                    limit= websocetCmds["data"]["limit"]
                                )                                      
                                responseData = response.data().result # open only results from the data                           
                                websocetCmds["return"] = responseData
                            except Exception as e:
                                logger.error(f"websocetManage() Connection error: klines() {e}")
                                websocetCmds["return"] = "error"
                                errorCount +=1  
                        case "trade":
                            try:
                                if basicSettings["useTelegram"]: #Write telegram message
                                    telegramMsg = websocetCmds["TelegramMsg"]
                                    await asyncio.wait_for(_telegramSend(telegramMsg), timeout=10)#Send telegram msg    
                                if websocetCmds["data"]["quantity"] > 0:
                                    print(f"want to sell {websocetCmds["data"]}")
                                    response = await connection.order_place(
                                        symbol=websocetCmds["data"]["symbol"],
                                        side=websocetCmds["data"]["side"],
                                        type= "MARKET",
                                        quantity =websocetCmds["data"]["quantity"],   #amount of Symbol 1 want to Sell 
                                    )    
                                else:
                                    print(f"want to buy {websocetCmds["data"]}")
                                    response = await connection.order_place(
                                        symbol=websocetCmds["data"]["symbol"],
                                        side=websocetCmds["data"]["side"],
                                        type= "MARKET",
                                        quote_order_qty=websocetCmds["data"]["quote_order_qty"] #quoted is the number of Symbol2 you want to spend or get
                                    )                            
                                responseData = response.data()
                                websocetCmds["return"] = responseData
                                logger.info(f"websocetManage() order posted succesfuly on {responseData.result.symbol} "
                                            f"with id = {responseData.result.client_order_id} | status = {responseData.result.status}")  
                                if basicSettings["useTelegram"]: #Write telegram message
                                    commission = 0.0
                                    commission_asset = "BNB"
                                    for part in responseData.result.fills: #go trough filled data for commision calculation 
                                        commission += float(part.commission)
                                        commission_asset = part.commission_asset  
                                    telegramMsg = ("Order filled response from Binance: \n "
                                                    f"id : {responseData.result.client_order_id} \n "                                   
                                                    f"time filled : {datetime.fromtimestamp(int(responseData.result.transact_time/1000))} \n "
                                                    f"side : {websocetCmds["data"]["side"]} \n "
                                                    f"trading pair : {websocetCmds["data"]["symbol"]} \n "
                                                    f"quantity = {responseData.result.executed_qty} of {websocetCmds["data"]["symbol1"]} \n "
                                                    f"quantity = {responseData.result.cummulative_quote_qty} of {websocetCmds["data"]["symbol2"]} \n "                                    
                                                    f"at avg. price = {round(float(responseData.result.cummulative_quote_qty)/  float(responseData.result.executed_qty), 8)} \n " 
                                                    f"commission = {commission} of {commission_asset}\n "
                                                    )
                                    await asyncio.wait_for(_telegramSend(telegramMsg), timeout=10)#Send telegram msg                                
                            except Exception as e:                                
                                logger.error(f"websocetManage() Connection error: order_place() {e}")
                                websocetCmds["return"] = "error"
                                if basicSettings["useTelegram"]: #Write telegram message
                                    telegramMsg = f"websocetManage() Connection error: order_place() {e}"
                                    await asyncio.wait_for(_telegramSend(telegramMsg), timeout=5)#Send telegram msg    
                                errorCount +=1                          
                        case "userData":
                            try:
                                response = await connection.account_status(omit_zero_balances=True)                     
                                responseData = response.data().result
                                websocetCmds["return"] = responseData
                            except Exception as e:
                                logger.error(f"websocetManage() Connection error: account_status() {e}")
                                websocetCmds["return"] = "error"
                                errorCount +=1     
                            
                    websocetCmds["cmd"] = "done"  
                event_websocetCmd.set()
            
            if errorCount > 2: #if errors excede X start reconnect
                logger.error(f"websocetManage() Connection error count: {errorCount}")
                with lock_websocetCmds:
                    websocetCmds["cmd"] = "error"       
                    websocetCmds["return"] = "error"
                break #Disconnect
            firstRun = False            
    except Exception as e:  
        with lock_websocetCmds:
            websocetCmds["cmd"] = "error"       
            websocetCmds["return"] = "error"
        logger.error(f"websocetManage() Connection lost or an error: {e}")        
        if basicSettings["useTelegram"]: #Write telegram message
            telegramMsg = f"websocetManage() Connection lost or an error: {e}"
            await asyncio.wait_for(_telegramSend(telegramMsg), timeout=5)#Send telegram msg 
    finally:     
        websocetCmds["connected"] = False    
        event_websocetCmd.set() #release functions if they are waiting for event
        await asyncio.sleep(1) 
        if websocetCmds["cmd"] != "disconnect":
            logger.error(f"websocetManage() Disconnecting due to error...")
        else:
            logger.info(f"websocetManage() Disconnect cmd was recived")
        event_websocetCmd.clear() #Block after released for response         
        if connection:                 
            await connection.close_connection(close_session=True)        

#ping server
def pingWebsocet():
    try:
        if not websocetCmds["connected"]: #Check for connection
            logger.error(f"pingWebsocet() no connection")
            return "error no connection"

        with lock_websocetCmds: #Lock to send cmds
            websocetCmds["cmd"] = "ping"
        #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread
        event_websocetCmd.wait()
        with lock_websocetCmds: #wait for result
            if "error" in websocetCmds["return"]:
                logger.error(f"pingWebsocet() error {websocetCmds["return"]}")
                return websocetCmds["return"]            
            if "return" in websocetCmds["return"]:
                logger.error(f"pingWebsocet() no data recived")
                return "No data recived"
                    
        logger.debug(f"pingWebsocet() return: { websocetCmds["return"]}")
        return websocetCmds["return"] # return data
    except Exception as e:
        logger.error(f"pingWebsocet() error: {e}")

#fetch historic data and store in csv
def fetch_histData(Symbol1, Symbol2, Interval, numData = 100):    
    try:
        if not websocetCmds["connected"]: #Check for connection
            logger.error(f"fetch_histData() no connection")
            return "error no connection"
        with lock_websocetCmds: #Lock to send cmds
            websocetCmds["data"] = {
                "symbol" : f"{Symbol1}{Symbol2}",
                "interval" : KlinesIntervalEnum[f"INTERVAL_{Interval}"].value,
                "limit" : numData
            }
            websocetCmds["cmd"] = "history"
        #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread  
        event_websocetCmd.wait()
        with lock_websocetCmds: #wait for result
            if "error" in websocetCmds["return"]:
                logger.error(f"fetch_histData() for {Symbol1}/{Symbol2} {Interval} error {websocetCmds["return"]}")
                return None
            if "return" in websocetCmds["return"]:
                logger.error(f"fetch_histData() for {Symbol1}/{Symbol2} {Interval} no data recived")
                return None
            kLineData = websocetCmds["return"] # copy data 
        
        logger.info(f"fetch_histData() for {Symbol1}/{Symbol2} {Interval} updated")
        return kLineData
    except Exception as e:
        logger.error(f"fetch_histData() error: {e}")

#Geting user data balances
def fetch_userData():
    
    try:
        if not websocetCmds["connected"]: #Check for connection
            logger.error(f"fetch_userData() no connection")
            return "error no connection"
        global my_balances
        with lock_websocetCmds: #Lock to send cmds
            websocetCmds["cmd"] = "userData"
        #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread
        event_websocetCmd.wait()
        with lock_websocetCmds: #wait for result
            if "error" in websocetCmds["return"]:
                logger.error(f"fetch_userData() error {websocetCmds["return"]}")
                return websocetCmds["return"]            
            if "return" in websocetCmds["return"]:
                logger.error(f"fetch_userData() no data recived")
                return "No data recived"
            data = websocetCmds["return"] # copy data       
        balances = data.balances
        for balance in balances:
            my_balances[balance.asset]={#"Asset" : balance.asset,  # craeate an list of assets
                "Available" : float(balance.free),
                "Locked" : float(balance.locked),
                "Total" : float(balance.free) + float(balance.locked)}

        with open(FILE_PATH_USER_DATA_JSON, "w") as jf: # save list of assets as JSON
            json.dump(my_balances, jf, ensure_ascii=False, indent=4)            
 
        csvFile = open(FILE_PATH_USER_DATA_CSV, "w", newline='')  #Open a Csv File
        csvFile_writer = csv.writer(csvFile, delimiter="," ) #set csv delimiter for writer
        #csvFile_writer.writerow(["Asset","Available", "locked", "Total"])
        for balance in balances:
            row = [balance.asset , float(balance.free) , float(balance.locked) , float(balance.free) + float(balance.locked)]
            csvFile_writer.writerow(row) # Write rows

        csvFile.close() # close de csv file
        #logger.info("fetch_userData() User data updated")

        #logger.info(f"my alocation {Symbol2}: {response2}")        

    except Exception as e:
        logger.error(f"fetch_userData() error: {e}")

#Geting exchange info once in the life time
def fetch_exchange_info(): #only fetch one ce in lifetime then save to json
    
    global exchange_info_data
    try:
        if os.path.exists(FILE_PATH_EXCHANGE_INFO): #if file exists load from file else get from exchange
            with open(FILE_PATH_EXCHANGE_INFO, "r") as jf: # save list of assets as JSON
                exchange_info_data = json.load(jf)
            return "load from file"
    
        if not websocetCmds["connected"]: #Check for connection
            logger.error(f"exchange_info() no connection")
            return "error no connection"
        with lock_websocetCmds: #Lock to send cmds
            websocetCmds["cmd"] = "exchange_info"
        #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread
        event_websocetCmd.wait()
        with lock_websocetCmds: #wait for result
            if "error" in websocetCmds["return"]:
                logger.error(f"exchange_info() error {websocetCmds["return"]}")
                return websocetCmds["return"]            
            if "return" in websocetCmds["return"]:
                logger.error(f"exchange_info() no data recived")
                return "error: No data recived"
            exchange_info_data = websocetCmds["return"] # copy data       
            #print(exchange_info_data)  
            with open(FILE_PATH_EXCHANGE_INFO, "w") as jf: # save list as JSON
                json.dump(exchange_info_data, jf, ensure_ascii=False, indent=4)        
            return "done"

    except Exception as e:
        logger.error(f"fetch_userData() error: {e}")

#Geting exchange info once in the life time
def read_exchange_info(): #only fetch one ce in lifetime then save to json
    if os.path.exists(FILE_PATH_EXCHANGE_INFO): #if file exists load from file else get from exchange
        with open(FILE_PATH_EXCHANGE_INFO, "r") as jf: # save list of assets as JSON
            exchange_info_data = json.load(jf)
        return exchange_info_data

#--send Trade to binance-----------------------------------------
def sendTrade(openTrade):
    try: 
        if not websocetCmds["connected"]: #Check for connection
            logger.error(f"sendTrade() no connection")
            return None   

        #prepare data to Send TRADE to API
        tradePair =  f"{openTrade[TRADE_TABLE_COL_SYMBOL_1]}{openTrade[TRADE_TABLE_COL_SYMBOL_2]}" #Get trading simbols row 2 and row 4                        
        roundnumQ = 5 #Get precision
        if len(exchange_info_data)>0:
            if tradePair in exchange_info_data:
                roundnumQ = exchange_info_data[tradePair]["order_precision"]

        if float(openTrade[TRADE_TABLE_COL_ASSET_S1_QT]) < 0.0:
            side="SELL"
            quote_order_qty= 0
            quantity = round(abs(float(openTrade[TRADE_TABLE_COL_ASSET_S1_QT])), roundnumQ) #When selling I want to sell the amount of Symbol1 I will recive Symbol2 depending on the market                        
        else:
            side="BUY"
            quote_order_qty= round(abs(float(openTrade[TRADE_TABLE_COL_ASSET_S2_QT])), roundnumQ)#When buying spend amount of symbol2 and recive amount of symbol1 depending on market
            quantity= 0
        telegramMsg = ("New order send to Binance \n "
                        f"send at time : {datetime.fromtimestamp(int(openTrade[TRADE_TABLE_COL_TIMESTAMP]/1000))} \n "
                        f"side : {side} \n "
                        f"trading pair : {tradePair} \n "
                        f"quantity = {round(openTrade[TRADE_TABLE_COL_ASSET_S1_QT],roundnumQ)} of {openTrade[TRADE_TABLE_COL_SYMBOL_1]} \n "
                        f"quantity = {round(openTrade[TRADE_TABLE_COL_ASSET_S2_QT],roundnumQ)} of {openTrade[TRADE_TABLE_COL_SYMBOL_2]} \n "
                        f"at price = {abs(openTrade[TRADE_TABLE_COL_PRICE])} {openTrade[TRADE_TABLE_COL_SYMBOL_2]} \n "
                        )
        with lock_websocetCmds: #Lock to send command and data
            websocetCmds["data"] = {
                "side" : side,
                "symbol" : tradePair,
                "quote_order_qty" : quote_order_qty,
                "quantity" : quantity,
                "symbol1" : openTrade[TRADE_TABLE_COL_SYMBOL_1],
                "symbol2" : openTrade[TRADE_TABLE_COL_SYMBOL_2],
            }
            websocetCmds["cmd"] = "trade"
            websocetCmds["TelegramMsg"] = telegramMsg
        logger.info(f"sendTrade() send order: {websocetCmds["data"]}")
        #wait for the communication module locks since Comm module is in another thread this can wait with stoping current thread       
        event_websocetCmd.wait()#wait for result  
        with lock_websocetCmds:                    
            if "error" in websocetCmds["return"]:
                logger.error(f"sendTrade() error {websocetCmds["return"]} for {side} trade on {tradePair}")                
                return None        
            if "return" in websocetCmds["return"]:
                logger.error(f"sendTrade() for {side} trade on {tradePair} no data recived")
                return None
            tradeData = websocetCmds["return"] # copy data

        tradeDataRecived = tradeData.result #Save data localy befor calling user data update
        logger.info(f"sendTrade() recive order data: {tradeDataRecived}")
        fetch_userData()
        if tradeDataRecived.status == "FILLED": #If filled update and return the trade order 
            openTradeRecive = openTrade.copy()
            openTradeRecive[TRADE_TABLE_COL_TIMESTAMP] = tradeDataRecived.transact_time
            openTradeRecive[TRADE_TABLE_COL_ID] = tradeDataRecived.client_order_id
            if float(openTrade[TRADE_TABLE_COL_ASSET_S1_QT]) > 0.0: #if buy then write positive values
                openTradeRecive[TRADE_TABLE_COL_ASSET_S1_QT] = float(tradeDataRecived.executed_qty)
                openTradeRecive[TRADE_TABLE_COL_ASSET_S2_QT] = -float(tradeDataRecived.cummulative_quote_qty)
            else:
                openTradeRecive[TRADE_TABLE_COL_ASSET_S1_QT] = -float(tradeDataRecived.executed_qty)
                openTradeRecive[TRADE_TABLE_COL_ASSET_S2_QT] = float(tradeDataRecived.cummulative_quote_qty)
            price = round(float(tradeDataRecived.cummulative_quote_qty)/  float(tradeDataRecived.executed_qty), 8)                                                     
            commission = 0.0
            commission_asset = "BNB"
            for part in tradeDataRecived.fills: #go trough filled data for commision calculation 
                commission += float(part.commission)
                commission_asset = part.commission_asset   
            openTradeRecive[TRADE_TABLE_COL_PRICE] = price #Calculated price maybe we can calculated out of every fill but dont think it is necesary
            openTradeRecive[TRADE_TABLE_COL_COMMISION] = commission
            openTradeRecive[TRADE_TABLE_COL_COMMISION_ASSET] = commission_asset           
             
            return openTradeRecive
        

    except Exception as e:
        logger.error(f"sendTrade() error: {e}")
        return None

