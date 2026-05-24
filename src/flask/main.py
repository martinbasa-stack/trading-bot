from src.constants import (
    BASE_DIR
)
from src.settings.main import settings_obj, credentials_obj

from .routes import bp

import logging
import os

from flask import Flask
from flask_simplelogin import SimpleLogin


def custom_user_validator(user):
    """
    Checks if the provided username and password are valid.
    The 'user' parameter is a dict {'username': '...', 'password': '...'}
    """    
    username = user.get("username")
    password = user.get("password")

    return credentials_obj.validate("user", username) and credentials_obj.validate("password", password)
    

#-----------FLASK APPLICATION
#Server Flask app
app = Flask(__name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")    
    )

app.config['LOGGER_NAME'] = 'main'
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/' # A secret key is required for flashing
SimpleLogin(app, login_checker=custom_user_validator)
# Register the blueprint containing the routes
app.register_blueprint(bp)
# Disable Werkzeug request logging
log = logging.getLogger('werkzeug')
log.disabled = True 


def run_flask_app():
    app.run(debug=False, 
            use_reloader=False,
            host=settings_obj.get("host"),
            port=settings_obj.get("Port")
            )
    app.root_path = BASE_DIR