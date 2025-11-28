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

import src #use only to call functions
from src import ( #For variables it has to be seperate for actualy sharing them
    my_balances,
    websocetCmds,
    streamCmds,
    passToFlask,
    settings_class
)

import threading
import asyncio
import atexit
import time
from datetime import datetime, timezone, timedelta

from flask import Flask
from flask_simplelogin import SimpleLogin

#---------------------SYSTEM -----------------------------
# Configure logger
# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_APP, mode="a") 
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#threads event
threads_shutDown_Event = threading.Event()

#--time vars
timeAppStart = 0
timePing = 0

#Cleanup at close app
def cleanup_function():
    logger.warning("Performing cleanup operations before exiting...") 
    print("Performing cleanup operations before exiting...") 
    src.shutDown()
    threads_shutDown_Event.set()
    src.disconnectAPI()
    time.sleep(settings_class.get("websocetManageLoopRuntime") + settings_class.get("klineStreamLoopRuntime") +1)

# Register the cleanup_function to be called on exit
atexit.register(cleanup_function)

#-----------FLASK APPLICATION
#Server Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/' # A secret key is required for flashing
app.config['SIMPLELOGIN_USERNAME'] = settings_class.get("user")
app.config['SIMPLELOGIN_PASSWORD'] = settings_class.get("password")
SimpleLogin(app)# Register the blueprint containing the routes
app.register_blueprint(src.bp)

# Disable Werkzeug request logging
log = logging.getLogger('werkzeug')
log.disabled = True 

#---------------------main task for data pull and strategy-----------------
def main():
    #Load settings for testing 
    global timePing, passToFlask
    if True: #try:
        now_utc = datetime.now(timezone.utc)
        timestamp_seconds = int(now_utc.timestamp())                

        conManageResponse = passToFlask["conManageResponse"]
        passToFlask["timeAppRunning"] = timedelta(seconds = timestamp_seconds - timeAppStart)          
        
        #Server conection managment for WebbSocet
        if (timePing  < (timestamp_seconds - int(settings_class.get("pingUpdate") *60)) or 
            timePing == 0 
            ): # check time last ping
            timePing = timestamp_seconds
            print(f"Running for {timedelta(seconds = timestamp_seconds - timeAppStart)}") 
            conManageResponse = src.pingWebsocet()
            logger.debug(f"Server Websocet ping response {conManageResponse}")
            if len(my_balances) == 0: #Refresh user data if there is no balances value
                src.fetch_userData()
        
        passToFlask["conManageResponse"] = conManageResponse
        #Check response of ping if no respons exit function
        if "error" in conManageResponse:  
            timePing = 0    
            return                  
        
        #Run strategies        
        src.strategyRun()

    #except Exception as e: 
    #    logger.error(f"Main error: {e}")

# Initialization -----------------------------------------------------
def _initialize():
    global timeAppStart, timePing
    try:
        logger.info("initialize() write data, wait for threads run,...")        
        now_utc = datetime.now(timezone.utc)
        timestamp_seconds = int(now_utc.timestamp()) 
        timeAppStart = timestamp_seconds
        timePing = timestamp_seconds #Load all from existing files at the start
        #Wait for threeds to start running
        i=7
        while i > 0:
            print(f"initialize() wait {i}s")
            time.sleep(1)
            i -=1
        #Get exchange info
        if websocetCmds["connected"]:
            logger.info("Get exchange info")
            print("initialize() Get exchange info")
            response = src.fetch_exchange_info()
        else:
            print("initialize() No connection") 
        #Read user data     
        time.sleep(1)
        if websocetCmds["connected"]:
            logger.info("initialize() Read user data")   
            print("initialize() Read user data") 
            src.fetch_userData()
        else:
            print("initialize() No connection") 


    except Exception as e: 
        logger.error(f"initialize() error: {e}")

#---------------------Streaming task Thread -----LOOP2------------------
def RUN_StreamLoop():
    print(f"RUN_StreamLoop() New thread Start") 
    logger.info("RUN_StreamLoop() New thread Start")
    backoff_attempt = 0
    backoff_base = 1.5
    reconnectPause = 30
    while not threads_shutDown_Event.is_set():
        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        task = None 
        logger.info(f"RUN_StreamLoop() Started") 
        try:
            task = loop2.create_task(src.klineStream(
                loopRuntime=settings_class.get("klineStreamLoopRuntime"),
                maxNoData=5,
                initialIntervalIndex=1
            ))
            loop2.run_until_complete(task)
        except Exception as e:
            logger.error(f"RUN_StreamLoop(): top-level exception: {e}")
            print(f"RUN_StreamLoop(): top-level exception: {e}")

        # Cancel any remaining tasks before closing the loop
        pending = asyncio.all_tasks(loop=loop2)
        for t in pending:
            t.cancel()
        loop2.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop2.close()
        logger.warning(f"RUN_StreamLoop(): cancelling {len(pending)} pending tasks")

        if not threads_shutDown_Event.is_set():
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 120)
            logger.error(f"RUN_StreamLoop() stopped unexpectedly - restarting after {sleep_time} s")
            print(f"RUN_StreamLoop() stopped unexpectedly - restarting after {sleep_time} s")
            time.sleep(sleep_time)

    logger.info("RUN_StreamLoop() Thread Stopped")
    print(f"RUN_StreamLoop() Thread Stopped") 

#---------------------Websocet API task Thread -----LOOP3------------------
def RUN_WebsocetLoop():
    logger.info(f"RUN_WebsocetLoop() New thread Start") 
    print(f"RUN_WebsocetLoop() New thread Start") 
    backoff_attempt = 0
    backoff_base = 1.5
    reconnectPause = 30

    while not threads_shutDown_Event.is_set():
        # Create and run the event loop       
        loop3 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop3)
        task = None
        logger.info(f"RUN_WebsocetLoop() Started") 
        #Runn loop for Websocet_loop   
        try:
            task = loop3.create_task(src.websocetManage(
                loopRuntime=settings_class.get("websocetManageLoopRuntime")
            ))        
            loop3.run_until_complete(task)
        except Exception as e:
            logger.error(f"RUN_WebsocetLoop(): top-level exception: {e}")
            print(f"RUN_WebsocetLoop(): top-level exception: {e}")

        # Cancel any remaining tasks before closing the loop
        pending = asyncio.all_tasks(loop=loop3)
        for t in pending:
            t.cancel()
        loop3.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop3), return_exceptions=True))
        loop3.close() 
        logger.warning(f"RUN_WebsocetLoop(): cancelling {len(pending)} pending tasks")

        if not threads_shutDown_Event.is_set(): #if shud down event is set no need to sleep
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 120)
            logger.error(f"RUN_WebsocetLoop() stopped unexpectedly - restarting after {sleep_time} s") 
            print(f"RUN_WebsocetLoop() stopped unexpectedly - restarting after {sleep_time} s") 
            time.sleep(sleep_time) 

    
    logger.info(f"RUN_WebsocetLoop() Thread Stopped") 
    print(f"RUN_WebsocetLoop() Thread Stopped") 

#-----------------------------------Flask Thread--------------------------------------
def RUN_flaskApp():
    logger.info("RUN_flaskApp() New thread Start")
    print("RUN_flaskApp() New thread Start")
    # because the reloader starts a new process which can cause issues with threads.
    app.run(debug=False, 
            use_reloader=False,
            host=settings_class.get("host"),
            port=settings_class.get("Port")
            )
    logger.info("RUN_flaskApp() Thread Stopped")
    print("RUN_flaskApp() Thread Stopped")
#Main task running forever and 3 threds one for Flask and one for Stream and one for Websocet
if __name__ == "__main__":        
    # Create and start the background task threads
    # Create and start the Flask thread
    flask_thread = threading.Thread(target=RUN_flaskApp)
    flask_thread.daemon = True # Allows the main program to exit even if threads are running
    flask_thread.start()

    # Create and start the Stream loop thread
    Stream_thread = threading.Thread(target=RUN_StreamLoop)
    Stream_thread.daemon = False
    Stream_thread.start()

    # Create and start the Websocet loop thread
    Websocet_thread = threading.Thread(target=RUN_WebsocetLoop)
    Websocet_thread.daemon = False
    Websocet_thread.start()

    #Initialize 
    _initialize()

 # The main thread can continue to run or wait
    try:
        FirstRun = True 
        while True:            
            # Main thread activity 
            if FirstRun:           
                logger.info("First run delay start")
                i=5
                while i > 0:
                    print(f"main() first run delay {i}s")
                    time.sleep(1)
                    i -=1          

            if websocetCmds["connected"] and streamCmds["connected"]: #check for websocet connection status
                main() #Call main function
            else:
                print("main() No connection") 
            time.sleep(settings_class.get("strategyUpdate")) #Will sleap for strategy update time
            FirstRun = False
    except KeyboardInterrupt:
        print("Program terminated by user...")
        threads_shutDown_Event.set()
        src.disconnectAPI()