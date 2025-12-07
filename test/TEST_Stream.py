import sys
sys.path.append("src")
import logging
from src.constants import (
    LOG_PATH_MAIN
)

# Configure the root logger (optional, for console output or general settings)
logging.basicConfig(level=logging.INFO,
                    filename=LOG_PATH_MAIN,
                    filemode="a", # a-> Append; w-> Clear and start from 0
                    format='%(asctime)s - %(levelname)s - %(message)s')

import src #use only to call functions
from src import  settings_obj

from src.binance import stream_manager_obj, stream_main #ping_websocet, fetch_exchange_info, fetch_user_data

import threading
import atexit
import time

from flask import Flask
from flask_simplelogin import SimpleLogin

#---------------------SYSTEM -----------------------------

#threads event
threads_shutdown_event = threading.Event()


#Cleanup at close app
def cleanup_function():
    print("Performing cleanup operations before exiting...") 
    src.shut_down()
    threads_shutdown_event.set()
    stream_manager_obj.disconnect()
    time.sleep(settings_obj.get("websocetManageLoopRuntime") + settings_obj.get("klineStreamLoopRuntime") +1)

# Register the cleanup_function to be called on exit
atexit.register(cleanup_function)

#-----------FLASK APPLICATION
#Server Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/' # A secret key is required for flashing
app.config['SIMPLELOGIN_USERNAME'] = settings_obj.get("user")
app.config['SIMPLELOGIN_PASSWORD'] = settings_obj.get("password")
SimpleLogin(app)# Register the blueprint containing the routes
app.register_blueprint(src.bp)

# Disable Werkzeug request logging
log = logging.getLogger('werkzeug')
log.disabled = True 



#---------------------Streaming task Thread -----LOOP2------------------
def thread_stream():
    print(f"thread_stream_loop() New thread Start") 
    backoff_attempt = 0
    backoff_base = 1.5
    reconnectPause = 30
    while not threads_shutdown_event.is_set():
        stream_main()

        if not threads_shutdown_event.is_set():
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 300)
            print(f"thread_stream_loop() stopped unexpectedly - restarting after {sleep_time} s")
            time.sleep(sleep_time)

    print(f"thread_stream_loop() Thread Stopped") 

#Main task running forever and 3 threds one for Flask and one for Stream and one for Websocet
if __name__ == "__main__":        
    # Create and start the background task threads
    # Create and start the Stream loop thread
    Stream_thread = threading.Thread(target=thread_stream)
    Stream_thread.daemon = False
    Stream_thread.start()



 # The main thread can continue to run or wait
    try:
        first_run = True 
        while True:            
            # Main thread activity 
            if first_run:           
                print("First run start")
            i=0
            step = 5
            data_current_time = 180
            run_loop = first_run
            while run_loop or not stream_manager_obj.all_streams_available() or not stream_manager_obj.all_data_current(data_current_time):
                if stream_manager_obj.all_streams_available():
                    run_loop = False
                else:
                    run_loop= True
                print(f"Wait for all streams to be available.")
                print(f"Waiting: {i} s ")
                print(f"Current active streams: {stream_manager_obj.get_active_list()}")
                print(f"Current active streams data: {stream_manager_obj._data}")
                time.sleep(step)
                i +=step
            
            stream_list = stream_manager_obj.get_active_list()
            key = next(iter(stream_list))
            if stream_manager_obj.is_connected():
                print("main() connection OK") 
            else:
                print("main() NO connection") 
                time.sleep(5)
            
            print(f"Current active streams: {stream_list}")
            if key:
                print(f"Current active streams data: {stream_manager_obj.get_full(key)}")

            time.sleep(settings_obj.get("strategyUpdate")) #Will sleap for strategy update time
            first_run = False
    except KeyboardInterrupt:
        print("Program terminated by user...")
        threads_shutdown_event.set()
        stream_manager_obj.disconnect()