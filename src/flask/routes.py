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
from src.market_history import market_history_obj, fear_gread_obj
from src.backtester.main import run_backtester

from .chart.format import FormatChart
from .form_utils import extract_strategy_from_form, extract_settings_from_form
from .log_utils import get_log_data, clear_log_data
from .views import trade_table_view, footer_text, strategy_status_view, assets_view, strategy_list

import copy

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
                           strategy_list = strategy_list(), 
                           footer_dis_text = footer_text()
                           )

@bp.route("/chart_trades", methods=['GET', 'POST'])
def chart_trades():
    ids = strategies_obj.get_id_list()
    if request.method == 'GET':
        idx = ids[0]
    if request.method == 'POST' and request.form:
        idx = int(request.form.get("load_select"))
        if idx not in ids:
            idx = ids[0]
    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=market_history_obj.get_table,
        get_trade_table=trade_manager_obj.get_table,
        get_fng_history=fear_gread_obj.get_hist
    )
    avgs, trades, candle_table, solo_indic, price_indic = formating_charts.get_all(idx)

    return render_template('chart_trades.html',
                            footer_dis_text = footer_text(), 
                            strategy_list = strategy_list(), 
                            strategyID = idx, 
                            TradeTables =  trade_table_view(),
                            activeStrategyData = strategy_status_view(),       
                            strategy = strategies_obj.get_by_id_dict(idx),                    
                            candles_json=candle_table,
                            trades_json=trades,
                            avgs= avgs,
                            price_indic = price_indic,
                            solo_indic = solo_indic
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
    return render_template('log_read.html', 
                           log_file_path = log_file_path,
                           log_lines=formatted_lines, 
                           footer_dis_text = footer_text()
                           )

@bp.route("/strategyStatus")
def strategyStatus():
    return render_template('strategy_status.html',  
                           activeStrategyData = strategy_status_view(), 
                            strategy_list = strategy_list(), 
                           footer_dis_text = footer_text()
                           )

@bp.route("/strategyManager", methods=['GET', 'POST'])
@login_required
def strategyManager():    
    usr_msg = ""
    if request.method == 'POST' and request.form:
        action = request.form.get("ActionButton")
        idx = (request.form.get("id")) # get Id
        if idx.isnumeric():
            idx = int(idx)
        if action == "Delete": #delete strategy settings
            if len(strategies_obj.get_id_list()) > 1 and idx != "backtester": #Do not delete last stratagy
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
                    " Orders will be send to exchange!")
            
        if action == "Reset": #reset clear trade data from .csv              
            trade_manager_obj.delete(idx,True)
            usr_msg=(f"Strategy with ID: {idx} was succesfuly RESTARTED \n"
                     " all trade data removed")

    return render_template('strategy_manager.html',
                        AllStrategySettings = strategies_obj.get_all_dict(),
                        activeStrategyData = strategy_status_view(), 
                        usrMsg = usr_msg,
                        strategy_list = strategy_list(), 
                        footer_dis_text = footer_text()
                        )

@bp.route("/strategySettings_html", methods=['GET'])
@login_required
def strategySettings_html():
    strategies_id_list = strategies_obj.get_id_list()
    usr_msg = ""
    scroll_id=strategies_id_list[0]        
    return render_template('strategy_settings.html',
                        AllStrategySettings = strategies_obj.get_all_dict(),
                        scrollId=scroll_id,
                        usrMsg=usr_msg, 
                        strategy_list = strategy_list(), 
                        footer_dis_text = footer_text()
                        )

@bp.route("/settings_chart", methods=['GET', 'POST'])
@login_required
def settings_chart():
    ids = strategies_obj.get_id_list()
    if request.method == 'GET':
        idx = ids[0]
    if request.method == 'POST' and request.form:
        idx = int(request.form.get("load_select"))
        if idx not in ids:
            idx = ids[0]
    
    return load_settings_chart(idx)

@bp.route("/backtester", methods=['GET', 'POST'])
@login_required
def backtester():
    msg = ""
    b1 = 0.5
    b2 = 10000.0
    if request.method == 'POST' and request.form:
        b1 = float(request.form.get("balance_s1"))
        b2 = float(request.form.get("balance_s2"))
        msg = run_backtester(b1,b2)
    return load_backtester(msg, b1, b2)

@bp.route("/backtester_load", methods=['POST'])
@login_required
def backtester_load():
    msg = "error"
    if request.method == 'POST' and request.form:
        idx = int(request.form.get("load_select"))
        data = strategies_obj.get_by_id(idx)
        strategy = copy.deepcopy(data)
        strategy.run = False
        strategy.asset_manager.paper_t = False       
        strategies_obj.update("backtester", strategy)             
        trade_manager_obj.update("backtester")
        msg = f"Strategy with ID {idx} succesfuly loaded to backtester."

    return load_backtester(msg)


@bp.route("/strategy_save", methods=['POST'])
@login_required
def strategy_save():
    strategies_id_list = strategies_obj.get_id_list()
    scroll_id=strategies_id_list[0]
    usr_msg = ""
    if request.method == 'POST' and request.form:
        try:
            action = request.form.get("ActionButton")
            location = request.form.get("location")
            if action is None: action = "Nothing"
            #-------------------------------
            #Check if symbol pair exists
            #-------------------------------
            s1 = request.form.get("Symbol1")
            s2 = request.form.get("Symbol2")
            pair =  f"{s1}{s2}"

            if not ws_manager_obj.check_pair_exist(pair):
                usr_msg = "ERROR: pair does not exist on exchange!"
                action = "None"

            if action == "backtester":
                strategy_id = action
                data = extract_strategy_from_form(request)
                strategies_obj.update(strategy_id, data)             
                trade_manager_obj.update(strategy_id)

                usr_msg = f"Settings for strategy ID {strategy_id} saved."
                return load_backtester(usr_msg)
                
            # ------------------------------
            # A) EDIT EXISTING STRATEGY
            # ------------------------------
            if action.isnumeric():
                strategy_id = int(action)
                data = extract_strategy_from_form(request)
                strategies_obj.update(strategy_id, data)             
                trade_manager_obj.update(strategy_id)
                scroll_id = strategy_id

                usr_msg = f"Settings for strategy ID {strategy_id} saved."

                if location == "chart":
                    return load_settings_chart(strategy_id)  

            # ------------------------------
            # B) ADD NEW STRATEGY
            # ------------------------------
            elif action == "AddNew":
                data = extract_strategy_from_form(request)
                new_id = strategies_obj.add(data)              
                trade_manager_obj.update(new_id)# after strategies_class the new ID exist and will be added

                usr_msg = f"Strategy with ID {new_id} created."  
                scroll_id = new_id
                
                if location == "chart":
                    return load_settings_chart(new_id)  
                
                if location == "backtester":
                    return load_backtester(usr_msg)  
            else:
                #usrMsg=f"error"
                usr_msg = f"Action Button internal error"
        except Exception as e:
            print(f"strategy_savel error: {e}")

    if location == "all":
        return render_template('strategy_settings.html',
                        AllStrategySettings = strategies_obj.get_all_dict(),
                        scrollId=scroll_id,
                        usrMsg=usr_msg, 
                        strategy_list = strategy_list(), 
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
                ws_manager_obj.fetch_user_data()
                usr_msg=f"Done."   

    return render_template("basic_settings.html",
                        my_basicSettings = settings_obj.all(),
                        usrMsg=usr_msg,
                        data = data,
                        exchange_info_data = exchange_info_data, 
                        footer_dis_text = footer_text()
                        )

def load_settings_chart(idx):
    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=market_history_obj.get_table,
        get_trade_table=trade_manager_obj.get_table,
        get_fng_history=fear_gread_obj.get_hist
    )
    avgs, trades, candle_table, solo_indic, price_indic = formating_charts.get_all(idx)

    return render_template('chart_settings.html',
                            AllStrategySettings = strategies_obj.get_all_dict(),
                            strategyID = idx, 
                            footer_dis_text = footer_text(),
                            strategy_list = strategy_list(),  
                            strategy = strategies_obj.get_by_id_dict(idx),                    
                            candles_json=candle_table,
                            trades_json=trades,
                            avgs= avgs,
                            price_indic = price_indic,
                            solo_indic = solo_indic
                           )

def load_backtester(msg, balance_s1 = 1, balance_s2 = 10000):
    idx = "backtester"
    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=market_history_obj.get_table,
        get_trade_table=trade_manager_obj.get_table,
        get_fng_history=fear_gread_obj.get_hist
    )
    avgs, trades, candle_table, solo_indic, price_indic = formating_charts.get_all(idx)

    return render_template('backtester.html',
                            AllStrategySettings = strategies_obj.get_all_dict(),
                            activeStrategyData = strategy_status_view(),  
                            TradeTables =  trade_table_view(),
                            strategyID = idx, 
                            footer_dis_text = footer_text(),
                            strategy_list = strategy_list(),   
                            strategy = strategies_obj.get_by_id_dict(idx),                    
                            candles_json=candle_table,
                            trades_json=trades,
                            avgs= avgs,
                            price_indic = price_indic,
                            solo_indic = solo_indic,
                            msg = msg,
                            balance_s1 = balance_s1,
                            balance_s2 = balance_s2
                           )