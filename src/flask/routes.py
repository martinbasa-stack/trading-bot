from ..constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN,
    LOG_PATH_BINANCE_API,
    LOG_PATH_SETTINGS,
    LOG_PATH_STRATEGY
)
from ..binance_API import ( 
    my_balances,
    activStreamList,
    read_exchange_info
)
from ..strategy import ( 
    advanceDCAstatus,
    fear_gread
)
from src.settings import strategies_class, settings_class
from src.trades import trade_manager_class
from .form_utils import extract_strategy_from_form, extract_settings_from_form
from .views import trade_table_view

from flask import Blueprint, render_template, request
from flask_simplelogin import SimpleLogin, login_required

passToFlask = {    
    "conManageResponse" : "None",
    "timeAppRunning" : ""
}

bp = Blueprint("flaskRoute", __name__)

def _formatLogLine(line):
    line = line.strip()
    if "ERROR" in line:
        return f'<span class="log-error">{line}</span>'
    elif "WARNING" in line:
        return f'<span class="log-warning">{line}</span>'
    elif "INFO" in line:
        return f'<span class="log-info">{line}</span>'
    return line

@bp.route("/")
def index():    
    return render_template('index.html',
                           MyBalance = my_balances, 
                           TradeTables = trade_table_view(), 
                           timeAppRunning=passToFlask["timeAppRunning"], 
                           pingResponse=passToFlask["conManageResponse"],
                           activStreamList=activStreamList,
                           fear_gread=fear_gread.data
                           )

@bp.route('/logs', methods=['GET', 'POST'])
def display_logs():
    log_file_path = LOG_PATH_MAIN
    try:
        if request.method == 'POST' and request.form:
            match request.form.get("ActionButton"):
                case "main":
                    log_file_path = LOG_PATH_MAIN
                case "app":
                    log_file_path = LOG_PATH_APP
                case "API":
                    log_file_path = LOG_PATH_BINANCE_API
                case "settings":
                    log_file_path = LOG_PATH_SETTINGS
                case "strategy":
                    log_file_path = LOG_PATH_STRATEGY
        with open(log_file_path, 'r') as f:
            # Read all lines and format them
            # Reading backwards might be better for large files
            # For simplicity, we read normally here.
            lines = f.readlines()
            reversed_lines  = lines[::-1]
            # Apply basic formatting for the display
            formatted_lines = [_formatLogLine(line) for line in reversed_lines]

    except FileNotFoundError:
        formatted_lines = ["Log file not found."]
    except Exception as e:
        formatted_lines = [f"An error occurred: {e}"]

    # Pass the list of formatted lines to the template
    return render_template('logRead.html', 
                           log_file_path = log_file_path,
                           log_lines=formatted_lines, 
                           timebpRunning=passToFlask["timeAppRunning"], 
                           pingResponse=passToFlask["conManageResponse"],
                           activStreamList=activStreamList,
                           fear_gread=fear_gread.data
                           )

@bp.route("/strategyStatus")
def strategyStatus():
    return render_template('strategyStatus.html',  
                           activeStrategyData = advanceDCAstatus, 
                           timeAppRunning=passToFlask["timeAppRunning"], 
                           pingResponse=passToFlask["conManageResponse"],
                           activStreamList=activStreamList,
                           fear_gread=fear_gread.data
                           )

@bp.route("/strategyManager", methods=['GET', 'POST'])
@login_required
def strategyManager():    
    usr_msg = ""
    if request.method == 'POST' and request.form:
        action = request.form.get("ActionButton")
        id_ = int(request.form.get("id")) # get Id

        if action == "Delete": #delete strategy settings
            if len(strategies_class.get_all()) > 1: #Do not delete last stratagy
                trade_manager_class.delete(id_,True)
                strategies_class.delete(id_)
                usr_msg=f"Strategy with ID: {id_} was succesfuly DELETED"
            else:
                usr_msg=f"Error can't DELETED last strategy"
        if action == "Run": #change to run
            strategies_class.set(id_,"run", True)
            usr_msg=f"Strategy with ID: {id_} was succesfuly STARTED"
        if action == "Stop": #stop 
            strategies_class.set(id_,"run", False)
            usr_msg=f"Strategy with ID: {id_} was succesfuly STOPPED"            
        if action == "Paper": #change to run
            strategies_class.set(id_,"paperTrading", True)
            usr_msg=(f"Strategy with ID: {id_} was succesfuly moved to paper trading: \n"
                     " NO orders will be send to exchange")
        if action == "Live": #stop 
            strategies_class.set(id_,"paperTrading", False)
            usr_msg=(f"Strategy with ID: {id_} was succesfuly lunched to LIVE: \n"
                    " orders will be send to exchange!")
        if action == "Reset": #reset clear trade data from .csv              
            trade_manager_class.delete(id_,True)
            usr_msg=(f"Strategy with ID: {id_} was succesfuly RESTARTED \n"
                     " all trade data removed")

    return render_template('strategyManager.html',
                        AllStrategySettings = strategies_class.get_all(),
                        activeStrategyData = advanceDCAstatus,
                        timeAppRunning=passToFlask["timeAppRunning"], 
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usr_msg,
                        activStreamList=activStreamList,
                        fear_gread=fear_gread.data
                        )

@bp.route("/strategySettings_html", methods=['GET', 'POST'])
@login_required
def strategySettings_html():
    all_strategies = strategies_class.get_all()
    usr_msg = ""
    scroll_id=all_strategies[0]["id"]
    if request.method == 'POST' and request.form:
        try:
            action = request.form.get("ActionButton")
            if action is None: action = "Nothing"
            #-------------------------------
            #Check if symbol pair exists
            #-------------------------------
            s1 = request.form.get("Symbol1")
            s2 = request.form.get("Symbol2")
            pair =  f"{s1}{s2}"

            if pair not in read_exchange_info():
                usr_msg = "ERROR: pair does not exist on exchange!"
                action = None

            # ------------------------------
            # A) EDIT EXISTING STRATEGY
            # ------------------------------
            if action.isnumeric():
                strategy_id = int(action)
                data = extract_strategy_from_form(request)
                strategies_class.update(strategy_id, data)                
                trade_manager_class.update(strategy_id)

                usr_msg = f"Settings for strategy ID {strategy_id} saved."
                scroll_id = strategy_id

            # ------------------------------
            # B) ADD NEW STRATEGY
            # ------------------------------
            elif action == "AddNew":
                data = extract_strategy_from_form(request)
                new_id = strategies_class.add(data)              
                trade_manager_class.update(new_id)# after strategies_class the new ID exist and will be added

                usr_msg = f"Strategy with ID {new_id} created."
                scroll_id = new_id            
            else:
                #usrMsg=f"error"
                usr_msg = f"Action Button internal error"
        except Exception as e:
            print(f"strategySettings.html error: {e}")
    
    return render_template('strategySettings.html',
                        AllStrategySettings = strategies_class.get_all(),
                        timeAppRunning=passToFlask["timeAppRunning"],
                        scrollId=scroll_id,
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usr_msg,
                        fear_gread=fear_gread.data,
                        activStreamList=activStreamList
                        )


@bp.route("/BasicSettings", methods=['GET', 'POST'])
@login_required
def BasicSettings(): 
    usrMsg=""
    data = ""
    exchange_info_data = read_exchange_info()
    if request.method == 'POST' and request.form:      
        if "SAVE" == request.form.get("ActionButton"):
            form_data = extract_settings_from_form(request)
            settings_class.update(form_data)
            usrMsg=f"General settings were succesfuly SAVED"

    return render_template("BasicSettings.html",
                        my_basicSettings = settings_class.all(),
                        timeAppRunning=passToFlask["timeAppRunning"],
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usrMsg,
                        data = data,
                        activStreamList=activStreamList,
                        fear_gread=fear_gread.data,
                        exchange_info_data = exchange_info_data
                        )
