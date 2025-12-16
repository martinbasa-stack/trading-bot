import sys
sys.path.append("src")
import logging
from src.constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN,
    BASE_DIR
)

# Configure the root logger (optional, for console output or general settings)
logging.basicConfig(level=logging.INFO,
                    filename=LOG_PATH_MAIN,
                    filemode="a", # a-> Append; w-> Clear and start from 0
                    format='%(asctime)s - %(levelname)s - %(message)s')

from src import  settings_obj, strategy_run, shut_down, bp
from src.strategy import asset_manager_obj
from src.telegram import send_telegram_msg
from src.market_history import history_run
from src.binance import stream_manager_obj, stream_main,  ws_manager_obj, websocet_main

import threading
import atexit
import time
import os
from datetime import datetime, timezone, timedelta

from flask import Flask
from flask_simplelogin import SimpleLogin

#---------------------SYSTEM -----------------------------
# Configure logger
# Create a logger for this module
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_APP, mode="a") 
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#threads event
threads_shutdown_event = threading.Event()

#--time vars
time_app_start = 0
time_ping = 0

#Cleanup at close app
def cleanup_function():
    logger.warning("Performing cleanup operations before exiting...") 
    print("Performing cleanup operations before exiting...") 
    shut_down()
    threads_shutdown_event.set()
    stream_manager_obj.disconnect()
    ws_manager_obj.disconnect()
    time.sleep(settings_obj.get("websocetManageLoopRuntime") + settings_obj.get("klineStreamLoopRuntime") +1)

# Register the cleanup_function to be called on exit
atexit.register(cleanup_function)

#-----------FLASK APPLICATION
#Server Flask app
app = Flask(__name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"))
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/' # A secret key is required for flashing
app.config['SIMPLELOGIN_USERNAME'] = settings_obj.get("user")
app.config['SIMPLELOGIN_PASSWORD'] = settings_obj.get("password")
SimpleLogin(app)# Register the blueprint containing the routes
app.register_blueprint(bp)

# Disable Werkzeug request logging
log = logging.getLogger('werkzeug')
log.disabled = True 

#---------------------main task for data pull and strategy-----------------
def main():
    first_run = True 
    report = False
    consol_update_count = 0
    start = _now()

    while True:            
        # Main thread activity 
        loop_update = int(settings_obj.get("strategyUpdate"))
        if first_run:           
            logger.info("First run start")
            print("First run start")

        if not first_run:
            _stream_data_monitor(180) #While loop until stream data is ok
        
        last_ping = ws_manager_obj.get_last_ping_resp()

        # Write status to console
        if consol_update_count > 3600 * int(settings_obj.get("statusUpdate")) or consol_update_count == 0:
            consol_update_count = 0
            update_msg = (
                   f"Websocket connected: {ws_manager_obj.is_connected()}"
                   f"\n     Last ping: {last_ping}"
                   f"\n Stream connected: {ws_manager_obj.is_connected()}"
                   f"\n     Oldest stream: {stream_manager_obj.oldest()} s, since {datetime.fromtimestamp(stream_manager_obj.oldest_timestamp())}"
                   f"\n     Current active streams: {stream_manager_obj.get_active_list()}"
                   )            
            print(f"Status update: {datetime.fromtimestamp(_now())} \n "
                  f"{update_msg}")
            logger.info(update_msg)

        consol_update_count +=loop_update        
        
        if ws_manager_obj.is_connected():#check for websocet connection status
            history_run() # Call historycal data
            strategy_run() #Call main function
            if report:
                consol_update_count = 0
                report = False
                now_seconds= _now()
                send_telegram_msg("WebSocket connection was lost!"                                  
                              f"\n Error time {datetime.fromtimestamp(start)} "
                              f"\n No data for {timedelta(seconds = now_seconds - start)}"
                              f"\n Reconnection SUCCESFUL.")
        else:
            if not report:
                consol_update_count= 0                
            report = True
            start = _now()
            time.sleep(5)
        time.sleep(loop_update) #Will sleap for strategy update time            
        first_run = False

def _stream_data_monitor(data_current_time):
    i=0
    step = 3
    run_loop = not stream_manager_obj.all_streams_available() or not stream_manager_obj.all_data_current(data_current_time)
    start = _now()
    while run_loop:
        if stream_manager_obj.all_streams_available() and stream_manager_obj.all_data_current(data_current_time):
            run_loop = False
            now_seconds = _now()
            send_telegram_msg(f"Stream connection was lost!"
                              f"\n Error time {datetime.fromtimestamp(start)}"
                              f"\n No data for {timedelta(seconds = now_seconds - start)}"
                              " \n Reconnection SUCCESFUL. ")

        print(f"Wait for all streams to be available.")
        print(f"Waiting: {i} s ")
        print(f"Current active streams: {stream_manager_obj.get_active_list()}")
        time.sleep(step)
        i +=step


# Initialization -----------------------------------------------------
def _initialize():
    global time_app_start, time_ping
    try:
        logger.info("initialize() write data, wait for threads run,...")        
        now_utc = datetime.now(timezone.utc)
        now_seconds = int(now_utc.timestamp()) 
        time_app_start = now_seconds
        time_ping = now_seconds #Load all from existing files at the start
        #Wait for threeds to start running        
        time.sleep(2)
        i=0        
        logger.info(f"initialize() Wait for connection with Websocet API")
        print(f"initialize() Wait for connection with Websocet API")
        while not ws_manager_obj.is_connected():
            print(f"initialize() Waiting: {i} s ")
            time.sleep(1)
            i +=1        

        logger.info(f"initialize() Waited: {i} s ")
        msg = (f"initialize \n Waited {i} s for connection with Websocet API \n")

        time.sleep(1)
        #Get exchange info
        logger.info("Get exchange info")
        print("initialize() Get exchange info")
        ws_manager_obj.fetch_exchange_info()

        #Read user data     
        time.sleep(1)
        logger.info("initialize() Read user data")   
        print("initialize() Read user data") 
        asset_manager_obj.update(ws_manager_obj.fetch_user_data())

        i=0
        run_loop = True
        data_current_time = 100
        logger.info(f"initialize() Wait for all streams to be available")
        while run_loop:
            if stream_manager_obj.all_streams_available() and stream_manager_obj.all_data_current(data_current_time):
                run_loop = False
            print(f"initialize() Wait for all streams to be available.")
            print(f"Waiting: {i} s ")
            print(f"Current active streams: {stream_manager_obj.get_active_list()}")
            time.sleep(1)
            i +=1            
            
        logger.info(f"initialize() Waited: {i} s ")
        msg = (f"{msg}"
            f"Waited {i} s for all streams to be available \n"
             f"Finished startup at: {datetime.fromtimestamp(_now())}")
        
        send_telegram_msg(msg)

    except Exception as e: 
        logger.error(f"initialize() error: {e}")

def _now():        
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp())     

#---------------------Streaming task Thread -----LOOP2------------------
def thread_stream():
    """Main stream thread loop"""
    print(f"thread_stream_loop() New thread Start") 
    logger.info("thread_stream_loop() New thread Start")
    backoff_attempt = 0
    backoff_base = 1.3
    reconnectPause = 30
    while not threads_shutdown_event.is_set():
        stream_main()

        if not threads_shutdown_event.is_set():
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 300)
            logger.error(f"thread_stream_loop() stopped unexpectedly - restarting after {sleep_time} s")
            print(f"thread_stream_loop() stopped unexpectedly - restarting after {sleep_time} s")
            time.sleep(sleep_time)

    logger.info("thread_stream_loop() Thread Stopped")
    print(f"thread_stream_loop() Thread Stopped") 

#---------------------Websocet API task Thread -----LOOP3------------------
def thread_websocket():
    """Main websocket thread loop"""
    logger.info(f"thread_websocket() New thread Start") 
    print(f"thread_websocket() New thread Start") 
    backoff_attempt = 0
    backoff_base = 1.2
    reconnectPause = 30

    while not threads_shutdown_event.is_set():
        websocet_main()        
          
        if not threads_shutdown_event.is_set(): #if shud down event is set no need to sleep
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 120)
            logger.error(f"thread_websocket() stopped unexpectedly - restarting after {sleep_time} s") 
            print(f"thread_websocket() stopped unexpectedly - restarting after {sleep_time} s") 
            time.sleep(sleep_time) 

    
    logger.info(f"thread_websocket() Thread Stopped") 
    print(f"thread_websocket() Thread Stopped") 

#-----------------------------------Flask Thread--------------------------------------
def thread_flaskApp():
    """Main Flask thread loop"""
    logger.info("thread_flaskApp() New thread Start")
    print("thread_flaskApp() New thread Start")

    time.sleep(10) #Delay app start
    # because the reloader starts a new process which can cause issues with threads.
    app.run(debug=False, 
            use_reloader=False,
            host=settings_obj.get("host"),
            port=settings_obj.get("Port")
            )
    app.root_path = BASE_DIR
    logger.info("thread_flaskApp() Thread Stopped")
    print("thread_flaskApp() Thread Stopped")

#Main task running forever and 3 threds one for Flask, one for Stream and one for Websocet
if __name__ == "__main__":        
    # Create and start the background task threads
    # Create and start the Flask thread
    flask_thread = threading.Thread(target=thread_flaskApp)
    flask_thread.daemon = True # Allows the main program to exit even if threads are running
    flask_thread.start()

    # Create and start the Stream loop thread
    Stream_thread = threading.Thread(target=thread_stream)
    Stream_thread.daemon = False
    Stream_thread.start()

    # Create and start the Websocet loop thread
    Websocet_thread = threading.Thread(target=thread_websocket)
    Websocet_thread.daemon = False
    Websocet_thread.start()

    #Initialize 
    _initialize()

 # The main thread can continue to run or wait
    try:
        main()
    except KeyboardInterrupt:
        print(f"Program terminated by user...")
    except Exception as e:
        print(f"Program terminated with exception: {e}")

    finally:
        threads_shutdown_event.set()
        ws_manager_obj.disconnect()
        stream_manager_obj.disconnect()