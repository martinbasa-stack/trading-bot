from src.constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN,
    LOG_PATH_BINANCE_API,
    LOG_PATH_SETTINGS,
    LOG_PATH_STRATEGY,
    LOG_PATH_SOLANA
)
from src.pyth.constants import LOG_PATH_PYTH
from src.assets.main import update_assets_q
from src.binance.websocket.thread import ws_manager_obj
from src.settings.main import strategies_obj, settings_obj
from src.strategy.trades.main import trade_manager_obj
from src.market_history.market import market_binance_hist_obj, fear_gread_obj, market_pyth_hist_obj
from src.backtester.main import run_backtester
from src.wallet.main import vault_obj, reload_wallet
from src.wallet.create import create_wallet, generate_seed_phrase
from src.solana_api.main import solana_man_obj

from .chart.format import FormatChart
from .form_utils import extract_strategy_from_form, extract_settings_from_form, save_credentials, check_strategy_pair
from .log_utils import get_log_data, clear_log_data
from .views import trade_table_view, footer_text, strategy_status_view, assets_binance_view, strategy_list, solana_tokens_list, assets_solana_view

import copy
import logging

from flask import Blueprint, render_template, request
from flask_simplelogin import login_required

# Create a logger for this module
logger = logging.getLogger("main")

bp = Blueprint("flaskRoute", __name__,
    template_folder="templates",
    static_folder="static",
               )

@bp.route("/")
@login_required
def index():    
    return render_template('index.html',
                           footer_dis_text = footer_text()
                           )


@bp.route("/wallet_unlock", methods=['GET', 'POST'])
@login_required
def wallet_unlock():
    try: 
        usr_msg=""
        if request.method == 'POST' and request.form:
            action = request.form.get("ActionButton")
            match action:
                case "UNLOCK":
                    password = request.form.get("password")                
                    usr_msg = "Unlocke FAILED!"
                    ok= vault_obj.unlock(password)                 
                    if ok:
                        solana_man_obj.wallet.load()
                        usr_msg = f"Wallets unlocked. Solana public address: {solana_man_obj.wallet.pub_key}"
                        update_assets_q()

    except Exception as e:
        logger.error(f"wallet_unlock route error: {e}")

    return render_template('assets.html',
                           binance_balance = assets_binance_view(), 
                           solana_balance = assets_solana_view(),
                           solana_wallet = solana_man_obj.wallet.pub_key,
                           footer_dis_text = footer_text(),
                           usr_msg = usr_msg
                           )


@bp.route("/assets")
@login_required
def assets():
    update_assets_q() 
    return render_template('assets.html',
                           binance_balance = assets_binance_view(), 
                           solana_balance = assets_solana_view(),
                           solana_wallet = solana_man_obj.wallet.pub_key,
                           footer_dis_text = footer_text()
                           )


@bp.route("/trades")
@login_required
def trades():    
    return render_template('trades.html',
                           TradeTables = trade_table_view(), 
                           strategy_list = strategy_list(), 
                           footer_dis_text = footer_text()
                           )

@bp.route("/chart_trades", methods=['GET', 'POST'])
@login_required
def chart_trades():
    ids = strategies_obj.get_id_list()
    if request.method == 'GET':
        idx = ids[0]
    if request.method == 'POST' and request.form:
        idx = int(request.form.get("load_select"))
        if idx not in ids:
            idx = ids[0]

    s = strategies_obj.get_by_id(idx)
    if market_binance_hist_obj.provider in s.type_s:
        hist_obj = market_binance_hist_obj
    elif market_pyth_hist_obj.provider in s.type_s:
        hist_obj = market_pyth_hist_obj
        

    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=hist_obj.get_table,
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
@login_required
def display_logs():
    log_file_path = LOG_PATH_MAIN
    try:
        if request.method == 'POST' and request.form:
            match request.form.get("ActionButton"):
                case "main":
                    log_file_path = LOG_PATH_MAIN
                case "app":
                    log_file_path = LOG_PATH_APP
                case "solana":
                    log_file_path = LOG_PATH_SOLANA
                case "binance":
                    log_file_path = LOG_PATH_BINANCE_API
                case "pyth":
                    log_file_path = LOG_PATH_PYTH
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
@login_required
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
            type_s = request.form.get("type")
            pair =  f"{s1}{s2}"
            pair_ok, usr_msg = check_strategy_pair(s1, s2, type_s)
            if not pair_ok:
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
                usr_msg = f"Action Button internal error {usr_msg}"
        except Exception as e:
            usr_msg = f"{usr_msg} strategy_save route error: {e}"
            logger.error(f"strategy_save route error: {e}")

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
    try: 
        usr_msg=""
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
                    update_assets_q()
                    usr_msg=f"Done."   
                
                case "SAVE CRED":
                    usr_msg= save_credentials(request)


    except Exception as e:
        logger.error(f"BasicSettings route error: {e}")

    return render_template("basic_settings.html",
                        my_basicSettings = settings_obj.all(),
                        usrMsg=usr_msg,
                        exchange_info_data = exchange_info_data, 
                        footer_dis_text = footer_text()
                        )

@bp.route("/wallet_setup", methods=['GET', 'POST'])
@login_required
def wallet_setup(): 
    usr_msg=""
    mnemo_phr = ""
    try:
        if request.method == 'POST' and request.form:
            action = request.form.get("ActionButton")
            match action:
                case "CREATE":
                    password = request.form.get("password")                    
                    mnemo_phr = request.form.get("mnemo")
                    if not mnemo_phr:
                        mnemo_phr = request.form.get("mnemo_custom")

                    usr_msg= create_wallet(password, mnemo_phr)
                    vault_obj = reload_wallet()
                    vault_obj.unlock(password)
                    solana_man_obj.wallet.load()
                    update_assets_q("Solana")
                    
                    usr_msg = f"{usr_msg} Wallet unlocked. Public key: {solana_man_obj.wallet.pub_key}"
                    
                case "NEW":
                    mnemo_phr = generate_seed_phrase()

    except Exception as e:
        logger.error(f"wallet_setup route error: {e}")

    return render_template("wallet_setup.html",
                        usrMsg=usr_msg,
                        phrase = mnemo_phr,
                        solana_pub_key = solana_man_obj.wallet.pub_key,
                        footer_dis_text = footer_text()
                        )

@bp.route("/solana_tokens", methods=['GET', 'POST'])
@login_required
def solana_tokens(): 
    usr_msg=""
    try:
        if request.method == 'POST' and request.form:
            action = request.form.get("ActionButton")
            match action:
                case "ADD":
                    mint = request.form.get("mint")        
                    new_t = solana_man_obj.tokens.new_token(mint)
                    if not new_t:
                        usr_msg = f"Token with mint {mint} does not exist!"
                    else:                        
                        usr_msg = f"Token {new_t.symbol} added!"

                case "DELETE":
                    symbol = request.form.get("symbol")
                    solana_man_obj.tokens.delete(symbol)
                    usr_msg = f"Token {symbol} removed."
        
            
            update_assets_q("Solana")
                
    except Exception as e:
        logger.error(f"solana_tokens route error: {e}")

    return render_template("solana_tokens.html",
                        usrMsg=usr_msg,
                        solana_tokens_list = solana_tokens_list(),
                        footer_dis_text = footer_text()
                        )

def load_settings_chart(idx):    
    s = strategies_obj.get_by_id(idx)

    hist_obj = market_binance_hist_obj
    if market_binance_hist_obj.provider in s.type_s:
        hist_obj = market_binance_hist_obj
    elif market_pyth_hist_obj.provider in s.type_s:
        hist_obj = market_pyth_hist_obj

    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=hist_obj.get_table,
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
    s = strategies_obj.get_by_id(idx)
    
    hist_obj = market_binance_hist_obj
    if market_binance_hist_obj.provider in s.type_s:
        hist_obj = market_binance_hist_obj
    elif market_pyth_hist_obj.provider in s.type_s:
        hist_obj = market_pyth_hist_obj
    formating_charts = FormatChart(
        strategies_obj=strategies_obj,
        get_hist_table=hist_obj.get_table,
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