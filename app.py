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

logger = logging.getLogger("main")

from src.settings.main import settings_obj
from src.binance.websocket.thread import  ws_manager_obj, websocet_main
from src.binance.stream.thread import binance_stream_man_obj, stream_main
from src.pyth.main import pyth_data_obj
from src.assets.main import assets_main_task, update_assets_q
from src.telegram.main import telegram_obj
from src.market_history.market import history_run, market_pyth_hist_obj, market_binance_hist_obj
from src.flask.main import run_flask_app
from src import  strategy_run, shut_down


import threading
import asyncio
import atexit
import time
import os
from datetime import datetime, timezone, timedelta

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

# Async event
async_shutdown_event = asyncio.Event()

#threads event
threads_shutdown_event = threading.Event()

#Cleanup at close app
def _cleanup_function():
    logger.warning("Performing cleanup operations before exiting...") 
    print("Performing cleanup operations before exiting...") 
    shut_down()
    async_shutdown_event.set()
    threads_shutdown_event.set()
    binance_stream_man_obj.disconnect()
    ws_manager_obj.disconnect()
    time.sleep(settings_obj.get("websocetManageLoopRuntime") + settings_obj.get("klineStreamLoopRuntime") +1)

# Register the cleanup_function to be called on exit
atexit.register(_cleanup_function)


# Console updata
def _status_update(consol_update_count): 
    # Write status to console
    if consol_update_count > 3600 * int(settings_obj.get("statusUpdate")) or consol_update_count == 0:
        consol_update_count = 0
        update_msg = _status_msg()
        print(f"Status update: {datetime.fromtimestamp(_now())} \n "
                f"{update_msg}")
        logger.info(update_msg)

    return consol_update_count

def _status_msg() -> str:
    last_ping = ws_manager_obj.get_last_ping_resp()
    return (
        f"Websocket connected: {ws_manager_obj.is_connected()}"
        f"\n     Last ping: {last_ping}"
        f"\n Binance Stream connected: {binance_stream_man_obj.is_connected()}"
        f"\n     Oldest stream: {binance_stream_man_obj.oldest()} s, since {datetime.fromtimestamp(binance_stream_man_obj.oldest_timestamp())}"
        f"\n     Current active streams: {binance_stream_man_obj.get_active_list()}"
        f"\n Pyth Stream connected: {pyth_data_obj.is_connected()}"
        f"\n     Oldest stream: {pyth_data_obj.oldest()} s, since {datetime.fromtimestamp(pyth_data_obj.oldest_timestamp())}"
        f"\n     Current active streams: {pyth_data_obj.get_active_list()}"
        )    
# Async 
# ====================================================================
# task manager
# --------------------------------------------------------------------
async def _task_manager():
    try:
        tasks : list[asyncio.Task] = []
        tasks.append(asyncio.create_task(_pyth_run()))
        tasks.append(asyncio.create_task(_hist_run()))
        tasks.append(asyncio.create_task(assets_main_task(async_shutdown_event)))
        #tasks.append(asyncio.create_task(_strategy_run()))
        tasks.append(asyncio.create_task(_assets_update()))
        
        update_assets_q()

        await telegram_obj.start(async_shutdown_event)

        all_tasks = asyncio.tasks.all_tasks()
        update_stat = 3600 * int(settings_obj.get("statusUpdate"))
        count= update_stat -1 
        loop_time = 2      
        while not async_shutdown_event.is_set():
            count +=loop_time
            if count > update_stat:
                for t in all_tasks:
                    coro_txt = str(t.get_coro())
                    coro_txt = coro_txt[1:coro_txt.find("at")]
                    print(f"{t.get_name()}: {coro_txt} is Done: {t.done()}") #Exception: {t.exception()} Cancelled: {t.cancelled()}
                    if t.done() and not async_shutdown_event.is_set():
                        logger.warning(f"Task finished unexpectedly {t}")
                count =0
            await asyncio.sleep(loop_time)

        await async_shutdown_event.wait()  

        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"_task_manager error: {e}")

# Assets Update 
# --------------------------------------------------------------------
async def _assets_update(watchdog : float = 3600):
    while not async_shutdown_event.is_set():
        update_assets_q()
        await asyncio.sleep(watchdog)
    
    pyth_data_obj.disconnect()

# Pyth connection run 
# --------------------------------------------------------------------
async def _pyth_run(watchdog : float = 1):
    while not async_shutdown_event.is_set():
        pyth_data_obj.run()
        await asyncio.sleep(watchdog)
    
    pyth_data_obj.disconnect()
        
# Market history run 
# --------------------------------------------------------------------
async def _hist_run(watchdog : float = 1.5):
    while not async_shutdown_event.is_set():
        await history_run() # Call historycal data
        await asyncio.sleep(watchdog)

# Strategy run 
# --------------------------------------------------------------------
async def _strategy_run():
    consol_update_count = 0
    while not async_shutdown_event.is_set():   
        loop_update = int(settings_obj.get("strategyUpdate")) 
        data_max_time = 180 # s for data from stream to be to old to continue 
        async with asyncio.TaskGroup() as tg:
            t1 = tg.create_task(_stream_data_monitor(async_shutdown_event, data_max_time, binance_stream_man_obj, "Binance"))
            t2 = tg.create_task(_bsc_websocket_data_monitor(async_shutdown_event))
            t3 = tg.create_task(_stream_data_monitor(async_shutdown_event, data_max_time, pyth_data_obj, "Pyth"))

        consol_update_count = _status_update(consol_update_count)
        consol_update_count +=loop_update

        if not market_pyth_hist_obj.data_update_req() and not market_binance_hist_obj.data_update_req():
            await strategy_run() # Call strategies
        await asyncio.sleep(loop_update)

# Data monitoring
# --------------------------------------------------------------------
async def _stream_data_monitor(shutdown_event : asyncio.Event, data_max_time, strem_obj, name, step = 4):
    i = strem_obj.oldest()
    run_loop = not strem_obj.all_streams_available() or not strem_obj.all_data_current(data_max_time)
    start = _now() - i
    while run_loop and not shutdown_event.is_set():
        all_available = strem_obj.all_streams_available()
        all_current = strem_obj.all_data_current(data_max_time)
        if all_available and all_current:
            run_loop = False
            now_seconds = _now()
            telegram_obj.send_msg(
                f"{name} Stream connection was lost!"
                f"\n Error time {datetime.fromtimestamp(start)}"
                f"\n No data for {timedelta(seconds = now_seconds - start)}"
                " \n Reconnection SUCCESFUL. "
                )

        print(f"Wait for all {name} streams to be available.")
        print(f"Waiting: {i} s ")
        print(f"Oldest stream: {strem_obj.oldest()} s")
        print(f"All available: {all_available} ")
        print(f"All current: {all_current} ")
        print(f"Current active streams: {list(strem_obj.get_active_list().keys())}")
        await asyncio.sleep(step)
        i +=step

async def _bsc_websocket_data_monitor( shutdown_event : asyncio.Event, step = 3):
    i=binance_stream_man_obj.oldest()
    run_loop = not ws_manager_obj.is_connected()
    start = _now() - i
    while run_loop and not shutdown_event.is_set():
        if ws_manager_obj.is_connected():
            run_loop = False
            now_seconds = _now()
            telegram_obj.send_msg(
                "Binance WebSocket connection was lost!"                                  
                f"\n Error time {datetime.fromtimestamp(start)} "
                f"\n No data for {timedelta(seconds = now_seconds - start)}"
                f"\n Reconnection SUCCESFUL."
                )

        print(f"Wait for Binance websocket to reconnect.")
        print(f"Waiting: {i} s ")
        await asyncio.sleep(step)
        i +=step

# Initialization -----------------------------------------------------
def initialize():
    try:
        logger.info("initialize() write data, wait for threads run,...")      
        data_current_time = 100
        #Wait for threeds to start running        
        time.sleep(2)
        i=0   
        stream_t = 0     
        logger.info(f"initialize() Wait for connection with Websocet API")
        print(f"initialize() Wait for connection with Websocet API")
        while not ws_manager_obj.is_connected():
            print(f"initialize() Waiting: {i} s ")            
            if not (binance_stream_man_obj.all_streams_available() and binance_stream_man_obj.all_data_current(data_current_time)):
                stream_t = i
            time.sleep(1)
            i +=1        

        logger.info(f"initialize() Waited: {i} s ")
        msg = (f"initialize \n Waited {i} s for connection with Websocet API \n")

        time.sleep(1)       
        #Get exchange info
        logger.info("Get exchange info")
        print("initialize() Get exchange info")
        ws_manager_obj.fetch_exchange_info()

        i =stream_t
        run_loop = True
        data_current_time = 100
        logger.info(f"initialize() Wait for all streams to be available")
        while run_loop:
            if binance_stream_man_obj.all_streams_available() and binance_stream_man_obj.all_data_current(data_current_time):
                run_loop = False
            print(f"initialize() Wait for all streams to be available.")
            print(f"Waiting: {i} s ")
            print(f"Current active streams: {binance_stream_man_obj.get_active_list()}")
            time.sleep(1)
            i +=1            
            
        logger.info(f"initialize() Waited: {i} s ")
        msg = (f"{msg}"
            f"Waited {i} s for all streams to be available \n"
            f"Finished startup at: {datetime.fromtimestamp(_now())}")
        
        # Start tasks 
        main_bot_thread.start()        
        flask_thread.start()
        telegram_obj.send_msg(msg)

    except Exception as e: 
        logger.error(f"initialize() error: {e}")

def _now():        
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp())     

# Threading
# ====================================================================
#---------------------Websocet API task Thread -----------------------
def thread_main_bot():
    """Main bot strategy thread loop"""
    logger.info(f"thread_main_bot() New thread Start") 
    print(f"thread_main_bot() New thread Start") 

    asyncio.run(_strategy_run())
    
    logger.info(f"thread_main_bot() Thread Stopped") 
    print(f"thread_main_bot() Thread Stopped") 

#---------------------Streaming task Thread -----------------------
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

#---------------------Websocet API task Thread -----------------------
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

    # because the reloader starts a new process which can cause issues with threads.
    run_flask_app()
    logger.info("thread_flaskApp() Thread Stopped")
    print("thread_flaskApp() Thread Stopped")

#Main task running forever and 3 threds one for Flask, one for Stream and one for Websocet
if __name__ == "__main__":        
    # Create and start the background task threads
    # Create and start the Flask thread
    flask_thread = threading.Thread(target=thread_flaskApp)
    flask_thread.daemon = True # Allows the main program to exit even if threads are running

    # Create and start the Stream loop thread
    Stream_thread = threading.Thread(target=thread_stream)
    Stream_thread.daemon = False
    Stream_thread.start()

    # Create and start the Websocet loop thread
    Websocet_thread = threading.Thread(target=thread_websocket)
    Websocet_thread.daemon = False
    Websocet_thread.start()

    
    # Create and start the Main bot strategy
    main_bot_thread = threading.Thread(target=thread_main_bot)
    main_bot_thread.daemon = False # Allows the main program to exit even if threads are running

    

 # The main thread can continue to run or wait
    try:
        #Initialize 
        initialize()
        #loop_manager()
        asyncio.run(_task_manager())
    except KeyboardInterrupt:
        print(f"Program terminated by user...")
    except Exception as e:
        print(f"Program terminated with exception: {e}")

    finally:
        async_shutdown_event.set()
        threads_shutdown_event.set()
        ws_manager_obj.disconnect()
        binance_stream_man_obj.disconnect()