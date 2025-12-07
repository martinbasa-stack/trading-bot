#Stream thread is running here
#=======================================================================
from src.settings import settings_obj, strategies_obj
from src.telegram import send_telegram_msg
from src.constants import(
    LOG_PATH_BINANCE_API,
    INTERVAL_LIST
)
from .models import StreamKline
from .manager import StreamManager

stream_data_obj = StreamManager(strategies_obj.generate_pairs_intervals)

import logging
import asyncio
import os
from datetime import datetime, timezone

from binance_sdk_spot.spot import (
    Spot,
    SPOT_WS_STREAMS_PROD_URL,
    ConfigurationWebSocketStreams
    )
from binance_common.constants import WebsocketMode
from binance_sdk_spot.websocket_streams.models import KlineIntervalEnum

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_BINANCE_API)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

#Threding variables for Stream
streamCmds={ #Used for communicating between stream_API thread and main thread
    "cmd": "done", #ping, history, trade, userData
    "data" : {},
    "return" : "", #Data that will be returned to not brake while loop
    "connected" : False
}


#Disconnect both by sending cmd to the threads
def disconnect_stream():
    print("Disconnecting from API")
    streamCmds["cmd"] = "disconnect"      

#------------------------------STREAM connection loop------------------------------------
async def kline_stream(loop_runtime = 5, max_no_data = 10, init_interval_ind = 1):
    global streamCmds
    connection_stream = None    
    # Create configuration for the WebSocket Streams
    configuration_ws_streams = ConfigurationWebSocketStreams(
        stream_url=os.getenv("STREAM_URL", SPOT_WS_STREAMS_PROD_URL),
        reconnect_delay=settings_obj.get("reconnect_delay"),
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
    time_old_data = 15 #Time in s where data is considered old
    
    interval_ind = init_interval_ind % len(INTERVAL_LIST) #Devides input index with lenght of list and returns what is left 4%6 = 2
    interval = INTERVAL_LIST[interval_ind]
    errorCount = 0

    try:
        # Initialize Spot client has to be here for reconection purpouse
        client = Spot(config_ws_streams=configuration_ws_streams)
        #Connect
        connection_stream = await client.websocket_streams.create_connection()
        await asyncio.sleep(2) #Pause affter connection established
        count_no_data = 0
        time_ping = int(datetime.now(timezone.utc).timestamp())
        active_streams = {}    #list of subscribed streams
        first_run = True  
        dataError = False    
        while True:  
            streamCmds["connected"] =True
            #Get time 
            now_seconds = _now()       
            #create a list of requested streams depending of settings
            requested_streams = {} 
            for pair in strategies_obj.generate_pairs_intervals().keys(): #run all unique pairs
                requested_streams[pair] = interval #interval is not important
            #Subscribe to requested streams if not subscribed
            for pair in requested_streams:                
                if not pair in active_streams: #If not in active stream list start a stream and add to the list   
                    stream = None
                    stream = await connection_stream.kline( 
                        symbol=pair,
                        interval=KlineIntervalEnum[f"INTERVAL_{interval}"].value,
                    ) 
                    stream.on("message", lambda data: _save_stream_data(data)) 
                    active_streams[pair] = requested_streams[pair]
                    logger.info(f"kLineStream() Subscribe to stream for: {pair} with interval = {requested_streams[pair]}")
                    del stream
            
            
            #Connection data integrity monitoring --------------------------------------------
            if stream_data_obj.oldest() > time_old_data and stream_data_obj.all_streams_available():
                time_old_data += 10 #Next limit longer
                count_no_data +=1
                #Handel NO DATA error--------------------------------------------
                if count_no_data >0:
                    logger.warning(f"kLineStream() No data recived from stream {count_no_data}")
                    time_ping = 0 #Requestr ping -> list_subscribe
                if count_no_data > max_no_data: #Generate logger message before unsubscribing from streams
                    logger.error(f"kLineStream(): No data recived from stream {count_no_data} > {max_no_data}! ")
                    print(f"kLineStream() No data recived from stream {count_no_data} > {max_no_data}! ")
                    #Set data error for procesing down the line
                    dataError = True                
                    count_no_data = 0  
            # Periodically verify server-side subscription list to detect mismatch
            if (now_seconds - time_ping) > int(settings_obj.get("pingUpdate") *60) and stream_data_obj.all_streams_available(): # check time last ping
                time_ping = now_seconds
                try:
                    allSubs = await connection_stream.list_subscribe()
                    if len(active_streams) > len(allSubs["result"]): #Error mismatch streams this happens when reconnection is needed
                        logger.warning(f"kLineStream() streams tracker error: server= {allSubs["result"]} | local= {active_streams}")
                        dataError = True
                    # rebuild activStreamList from server response
                    active_streams.clear()
                    for sub in allSubs["result"]:    # update active stream list  
                        str_formated, _, _  = sub.partition("@") 
                        active_streams[str.upper(str_formated)] = interval
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
                requested_streams.clear() #this will unsubscribe from all
            #Unsubscribing logic------------------------------------------------------
            for Pair in list(active_streams.keys()):
                if not Pair in requested_streams:
                    try:
                        #Remove from stream
                        logger.info(f"kLineStream() Unsubscribe from stream for: {Pair} with interval = {active_streams[Pair]}")
                        strFormat = f"{str.lower(Pair)}@kline_{active_streams[Pair]}"
                        await connection_stream.unsubscribe(streams=strFormat)
                        del active_streams[Pair]  #Delete active stream list
                    except Exception as e:
                        logger.error(f"kLineStream() unsubscribe error: {e}")
                        errorCount +=1 #Count errors for disconnect

            first_run = False
            if errorCount > 2: #if errors excede X start reconnect
                logger.error(f"kLineStream() Connection error count: {errorCount}")
                break #Disconnect

            if streamCmds["cmd"] == "disconnect": #Disconnecting
                break #exit while loop
            await asyncio.sleep(loop_runtime)
    except Exception as e:
        logger.error(f"kLineStream() Connection lost or error: {e}")
        if settings_obj.get("useTelegram"): #Write telegram message
            telegram_msg = f"kLineStream() Connection lost or error: {e}"
            send_telegram_msg(telegram_msg)#Send telegram msg 

    finally:
        streamCmds["connected"] =False
    try:
        if connection_stream:
            await asyncio.wait_for(connection_stream.close_connection(close_session=True), timeout=10)
    except Exception as e:
        logger.error(f"kLineStream(): close connection error: {e}")
    try:
        if client:
            # if the SDK has a cleanup method, call it (some SDKs provide close_connections())
            if hasattr(client, "close_connections"):
                await asyncio.sleep(0)   # yield to event loop
                await asyncio.wait_for(client.close_connections(), timeout=10)        
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
    
    del client

 
#Function for catching stream data
def _save_stream_data(data):
    try:
        #print(f"Stream data recived for: {data.s}")
        if data:
            kline = StreamKline(
                time_ms= int(data.E),
                open_= float(data.k.o),
                close= float(data.k.c),
                high=float(data.k.h),
                low= float(data.k.l),
                volume= float(data.k.v),
                interval= data.k.i
            )
            #print(f"stream pair {data.s} kline :{kline}")
            stream_data_obj.set(data.s, kline)
    except Exception as e:
        logger.error(f"Save Stream data() error: {e}")

def _now() -> int:    
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp())  