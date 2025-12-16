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

from src import  settings_obj
from src.flask.routes import bp

import os

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


#-----------FLASK APPLICATION
#Server Flask app
test_app = Flask("test",
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"))
test_app.config['SECRET_KEY'] = b'_5#y2L"F8z\n\xec]/' # A secret key is required for flashing
test_app.config['SIMPLELOGIN_USERNAME'] = settings_obj.get("user")
test_app.config['SIMPLELOGIN_PASSWORD'] = settings_obj.get("password")
SimpleLogin(test_app)# Register the blueprint containing the routes
test_app.register_blueprint(bp)

# Disable Werkzeug request logging
log = logging.getLogger('werkzeug')
log.disabled = True 

#-----------------------------------Flask Thread--------------------------------------
def thread_flaskApp():
    """Main Flask thread loop"""
    logger.info("thread_flaskApp() New thread Start")
    print("thread_flaskApp() New thread Start")

    # because the reloader starts a new process which can cause issues with threads.
    test_app.run(debug=False, 
            use_reloader=False,
            host=settings_obj.get("host"),
            port="5001"
            )
    test_app.root_path = BASE_DIR
    logger.info("thread_flaskApp() Thread Stopped")
    print("thread_flaskApp() Thread Stopped")

#Main task running forever and 3 threds one for Flask, one for Stream and one for Websocet
if __name__ == "__main__":        
    
 # The main thread can continue to run or wait
    try:
        thread_flaskApp()
    except KeyboardInterrupt:
        print(f"Program terminated by user...")
    except Exception as e:
        print(f"Program terminated with exception: {e}")
