import sys
sys.path.append("src")
import logging
from src.constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN
)

# Configure the root logger (optional, for console output or general settings)
logging.basicConfig(level=logging.INFO,
                    filename=LOG_PATH_MAIN,
                    filemode="a", # a-> Append; w-> Clear and start from 0
                    format='%(asctime)s - %(levelname)s - %(message)s')

from src import  settings_obj
from src.strategy import asset_manager_obj

from src.binance import ws_manager_obj
from src.binance.websocket.thread import websocet_main

import threading
import asyncio
import atexit
import time
from datetime import datetime, timezone, timedelta


#---------------------SYSTEM -----------------------------
#threads event
threads_shutdown_event = threading.Event()

#Cleanup at close app
def cleanup_function():
    print("Performing cleanup operations before exiting...") 
    threads_shutdown_event.set()
    ws_manager_obj.disconnect()
    time.sleep(settings_obj.get("websocetManageLoopRuntime") + settings_obj.get("klineStreamLoopRuntime") +1)

# Register the cleanup_function to be called on exit
atexit.register(cleanup_function)


# Initialization -----------------------------------------------------
def _initialize():
    try:       
        now_utc = datetime.now(timezone.utc)
        now_seconds = int(now_utc.timestamp()) 
        #Wait for threeds to start running
        i=0        
        while not ws_manager_obj._ws_cmds.connected:
            print(f"initialize() Waiting: {i} s ")
            time.sleep(1)
            i +=1
        

        time.sleep(3)
        #Get exchange info
        print("initialize() Get exchange info")
        ws_manager_obj.fetch_exchange_info()

        #Read user data     
        time.sleep(1)
        if ws_manager_obj._ws_cmds.connected: 
            print("initialize() Read user data") 
            asset_manager_obj.update(ws_manager_obj.fetch_user_data())
        else:
            print("initialize() No connection") 
    except Exception as e: 
        print(f"initialize() error: {e}")

#---------------------Websocet API task Thread -----LOOP3------------------
def thread_websocet_loop():
    print(f"thread_websocet_loop() New thread Start") 
    backoff_attempt = 0
    backoff_base = 1.5
    reconnectPause = 30

    while not threads_shutdown_event.is_set():
        websocet_main()

        if not threads_shutdown_event.is_set(): #if shud down event is set no need to sleep
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 300)
            print(f"thread_websocet_loop() stopped unexpectedly - restarting after {sleep_time} s") 
            time.sleep(sleep_time) 
            if sleep_time > 300:
                backoff_attempt = 0
        time.sleep(5) 
    print(f"thread_websocet_loop() Thread Stopped") 


#Main task running forever and 3 threds one for Flask and one for Stream and one for Websocet
if __name__ == "__main__":        
    # Create and start the background task threads

    # Create and start the Websocet loop thread
    Websocet_thread = threading.Thread(target=thread_websocet_loop)
    Websocet_thread.daemon = False
    Websocet_thread.start()

    #Initialize 
    _initialize()

 # The main thread can continue to run or wait
    try:
        first_run = True 
        while True:            
            # Main thread activity 
            if first_run:           
                print("First run delay start")
            
            ws_manager_obj.ping_ws()
            print(f"Last ping response {ws_manager_obj.get_last_ping_resp()}")

            kline_data = ws_manager_obj.fetch_kline("BTC", "USDC", "15m", 1000)
            if kline_data:
                print(f"Last kline_data {kline_data[-1]}")
            
            if ws_manager_obj.is_connected():# and stream_data_class.all_streams_available(): #check for websocet connection status
                print("main() websocet connected OK") 
            else:
                print("main() No websocet connection") 
                time.sleep(5)
            time.sleep(3) # sleap shorter for testing            
            first_run = False
    except KeyboardInterrupt:
        print("Program terminated by user...")
        threads_shutdown_event.set()
        ws_manager_obj.disconnect()