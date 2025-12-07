from src.constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN,
    LOG_PATH_BINANCE_API,
    LOG_PATH_SETTINGS,
    LOG_PATH_STRATEGY
)
from src.binance import ws_manager_obj
from src.settings import strategies_obj, settings_obj
from src.strategy import trade_manager_obj

from .form_utils import extract_strategy_from_form, extract_settings_from_form
from .log_utils import get_log_data, clear_log_data
from .views import trade_table_view, footer_text, strategy_status_view, assets_view

from flask import Blueprint, render_template, request
from flask_simplelogin import login_required

bp = Blueprint("flaskRoute", __name__,
    template_folder="templates",
    static_folder="static",
               )

@bp.route("/")
def index():    
    return render_template('index.html',
                           MyBalance = assets_view(), 
                           footer_dis_text = footer_text()
                           )

@bp.route("/trades")
def trades():    
    return render_template('trades.html',
                           TradeTables = trade_table_view(), 
                           footer_dis_text = footer_text()
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

        formatted_lines = get_log_data(log_file_path)

    except FileNotFoundError:
        formatted_lines = ["Log file not found."]
    except Exception as e:
        formatted_lines = [f"An error occurred: {e}"]

    # Pass the list of formatted lines to the template
    return render_template('logRead.html', 
                           log_file_path = log_file_path,
                           log_lines=formatted_lines, 
                           footer_dis_text = footer_text()
                           )

@bp.route("/strategyStatus")
def strategyStatus():
    return render_template('strategyStatus.html',  
                           activeStrategyData = strategy_status_view(), 
                           footer_dis_text = footer_text()
                           )

@bp.route("/strategyManager", methods=['GET', 'POST'])
@login_required
def strategyManager():    
    usr_msg = ""
    if request.method == 'POST' and request.form:
        action = request.form.get("ActionButton")
        idx = int(request.form.get("id")) # get Id

        if action == "Delete": #delete strategy settings
            if len(strategies_obj.get_id_list()) > 1: #Do not delete last stratagy
                trade_manager_obj.delete(idx,True)
                strategies_obj.delete(idx)
                usr_msg=f"Strategy with ID: {idx} was succesfuly DELETED"
            else:
                usr_msg=f"Error can't DELETED last strategy"
        if action == "Run": #change to run
            strategies_obj.set_run(idx, True)
            trade_manager_obj.update(idx)
            usr_msg=f"Strategy with ID: {idx} was succesfuly STARTED"
        if action == "Stop": #stop 
            strategies_obj.set_run(idx, False)
            trade_manager_obj.update(idx)
            usr_msg=f"Strategy with ID: {idx} was succesfuly STOPPED"            
        if action == "Paper": #change to run
            strategies_obj.set_paper_t(idx, True)
            trade_manager_obj.update(idx)
            usr_msg=(f"Strategy with ID: {idx} was succesfuly moved to paper trading: \n"
                     " NO orders will be send to exchange")
        if action == "Live": #stop 
            strategies_obj.set_paper_t(idx, False)
            trade_manager_obj.update(idx)
            usr_msg=(f"Strategy with ID: {idx} was succesfuly lunched to LIVE: \n"
                    " orders will be send to exchange!")
        if action == "Reset": #reset clear trade data from .csv              
            trade_manager_obj.delete(idx,True)
            usr_msg=(f"Strategy with ID: {idx} was succesfuly RESTARTED \n"
                     " all trade data removed")

    return render_template('strategyManager.html',
                        AllStrategySettings = strategies_obj.get_all_dict(),
                        activeStrategyData = strategy_status_view(), 
                        usrMsg = usr_msg,
                        footer_dis_text = footer_text()
                        )

@bp.route("/strategySettings_html", methods=['GET', 'POST'])
@login_required
def strategySettings_html():
    strategies_id_list = strategies_obj.get_id_list()
    usr_msg = ""
    scroll_id=strategies_id_list[0]
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

            if not ws_manager_obj.check_pair_exist(pair):
                usr_msg = "ERROR: pair does not exist on exchange!"
                action = None

            # ------------------------------
            # A) EDIT EXISTING STRATEGY
            # ------------------------------
            if action.isnumeric():
                strategy_id = int(action)
                data = extract_strategy_from_form(request)
                strategies_obj.update(strategy_id, data)             
                trade_manager_obj.update(strategy_id)

                usr_msg = f"Settings for strategy ID {strategy_id} saved."
                scroll_id = strategy_id

            # ------------------------------
            # B) ADD NEW STRATEGY
            # ------------------------------
            elif action == "AddNew":
                data = extract_strategy_from_form(request)
                new_id = strategies_obj.add(data)              
                trade_manager_obj.update(new_id)# after strategies_class the new ID exist and will be added

                usr_msg = f"Strategy with ID {new_id} created."
                scroll_id = new_id            
            else:
                #usrMsg=f"error"
                usr_msg = f"Action Button internal error"
        except Exception as e:
            print(f"strategySettings.html error: {e}")
    
    return render_template('strategySettings.html',
                        AllStrategySettings = strategies_obj.get_all_dict(),
                        scrollId=scroll_id,
                        usrMsg=usr_msg, 
                        footer_dis_text = footer_text()
                        )

@bp.route("/BasicSettings", methods=['GET', 'POST'])
@login_required
def BasicSettings(): 
    usr_msg=""
    data = ""
    exchange_info_data = ws_manager_obj.get_exchange_info()
    if request.method == 'POST' and request.form:
        action = request.form.get("ActionButton")
        match action:
            case "SAVE":
                form_data = extract_settings_from_form(request)
                settings_obj.update(form_data)
                usr_msg=f"General settings were succesfuly SAVED"

            case "force_update":            
                usr_msg=f"ERROR while fetching update."
                exchange_info_data = ws_manager_obj.fetch_exchange_info(True)
                usr_msg=f"Exchange data updated."

            case "ping":                
                usr_msg=f"ERROR while pinging server."
                ws_manager_obj.ping_ws()
                usr_msg=f"Done."
                

    return render_template("BasicSettings.html",
                        my_basicSettings = settings_obj.all(),
                        usrMsg=usr_msg,
                        data = data,
                        exchange_info_data = exchange_info_data, 
                        footer_dis_text = footer_text()
                        )
