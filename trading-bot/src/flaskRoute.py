from .constants import (
    LOG_PATH_APP,
    LOG_PATH_MAIN,
    LOG_PATH_BINANCE_API,
    LOG_PATH_SETTINGS,
    LOG_PATH_STRATEGY
)
from .binance_API import ( 
    my_balances,
    activStreamList,
    exchange_info_data
)
from .strategy import ( 
    tradeTablesView,
    advanceDCAstatus,
    fearAndGreed
)
from .settings import saveBsettings, saveStrSettings, loadBsettings, loadStrSettings

import os

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
                           TradeTables = tradeTablesView, 
                           timeAppRunning=passToFlask["timeAppRunning"], 
                           pingResponse=passToFlask["conManageResponse"],
                           activStreamList=activStreamList,
                           fearAndGreed=fearAndGreed
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
                           fearAndGreed=fearAndGreed
                           )

@bp.route("/strategyStatus")
def strategyStatus():
    return render_template('strategyStatus.html',  
                           activeStrategyData = advanceDCAstatus, 
                           timeAppRunning=passToFlask["timeAppRunning"], 
                           pingResponse=passToFlask["conManageResponse"],
                           activStreamList=activStreamList,
                           fearAndGreed=fearAndGreed
                           )

@bp.route("/strategyManager", methods=['GET', 'POST'])
@login_required
def strategyManager():
    strategySettings = loadStrSettings()
    usrMsg = ""
    if request.method == 'POST' and request.form:
        index= -1 #Set id our of scope 
        id= int(request.form.get("id")) # get Id 
        for i, strategy in enumerate(strategySettings):#Find index 
            if id == strategy["id"]:
                index = i
        if index >= 0 : #Button was not numeric or was not add
            if request.form.get("ActionButton") == "Delete": #delete strategy settings
                if len(strategySettings) > 1:
                    filePatern = f"_{strategySettings[index]["id"]}_.csv"
                    entries = os.listdir("data") # get all file names in directory
                    for entry in entries:
                        if filePatern in entry:    # filter name by indexy                   
                            os.remove(f"data/{entry}") #remove file
                    del strategySettings[index] #Remove Trade table for paper and live trading
                    usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly DELETED"
                else:
                    usrMsg=f"Error can't DELETED last strategy"
            if request.form.get("ActionButton") == "Run": #change to run
                strategySettings[index]["run"] = True
                usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly STARTED"
            if request.form.get("ActionButton") == "Stop": #stop 
                strategySettings[index]["run"] = False
                usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly STOPPED"            
            if request.form.get("ActionButton") == "Paper": #change to run
                strategySettings[index]["paperTrading"] = True
                usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly moved to paper trading: no orders will be transmited to exchange"
            if request.form.get("ActionButton") == "Live": #stop 
                strategySettings[index]["paperTrading"] = False
                usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly lunched to LIVE: orders will be send to exchange!"
            if request.form.get("ActionButton") == "Reset": #reset clear trade data from .csv  
                filePatern = f"_{strategySettings[index]["id"]}_.csv"
                entries = os.listdir("data") # get all file names in directory
                for entry in entries:
                    if filePatern in entry:    # filter name by indexy                   
                        os.remove(f"data/{entry}") #remove file
                usrMsg=f"Strategy with ID: {request.form.get("id")} was succesfuly RESTARTED all trade data removed"
            saveStrSettings(strategySettings)

    return render_template('strategyManager.html',
                        AllStrategySettings = strategySettings,
                        activeStrategyData = advanceDCAstatus,
                        timeAppRunning=passToFlask["timeAppRunning"], 
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usrMsg,
                        activStreamList=activStreamList,
                        fearAndGreed=fearAndGreed
                        )

@bp.route("/strategySettings_html", methods=['GET', 'POST'])
@login_required
def strategySettings_html():
    strategySettings = loadStrSettings()
    usrMsg = ""
    scrollId=strategySettings[0]["id"]
    if request.method == 'POST' and request.form:
        try:
            #Check if symbol pair exists
            Pair = request.form.get("Symbol1") + request.form.get("Symbol2")
            PairOK= True
            if len(exchange_info_data) > 2:
                if not Pair in exchange_info_data:
                    usrMsg = "ERROR no such pair traiding on exchange!"
                    PairOK = False

            index= -1 #Set id our of scope 
            usrMsg=f"error"
            if request.form.get("ActionButton").isnumeric() and PairOK: # if it is numeric it will edit existing settings
                id= int(request.form.get("ActionButton")) # get Id 
                for i, strategy in enumerate(strategySettings): #Find index 
                    if id == strategy["id"]:
                        index = i
                usrMsg=f"Settings of strategy with ID: {id} were succesfuly SAVED"
            
            if "AddNew" == request.form.get("ActionButton") and PairOK: # if it is numeric it will edit existing settings
                tempList = []
                for strategy in strategySettings: #generate list of existing id-s
                    tempList.append(strategy["id"])
                index= len(strategySettings) #set index to the current lenght before appending
                id = 0
                while id in tempList: # increse id untill it is not in the list and it is unuque
                    id +=1
                strategySettings.append({}) 
                usrMsg=f"Strategy with ID: {id} was succesfuly ADDED to trading strategies"              

            if index >= 0 : #Button was not numeric or was not add
                strategySettings[index]["id"] = id                     
                strategySettings[index]["name"] = request.form.get("name")
                strategySettings[index]["type"] = "AdvancedDCA"  #Currently no other type possible
                strategySettings[index]["Symbol1"] = request.form.get("Symbol1")
                strategySettings[index]["Symbol2"] = request.form.get("Symbol2")
                if request.form.get("run") == None:
                    strategySettings[index]["run"] = False
                else:
                    strategySettings[index]["run"] = True
                if request.form.get("paperTrading") == None:
                    strategySettings[index]["paperTrading"] = False
                else:
                    strategySettings[index]["paperTrading"] = True  
                if request.form.get("candleCloseOnly") == None:
                    strategySettings[index]["candleCloseOnly"] = False
                else:
                    strategySettings[index]["candleCloseOnly"] = True              
                strategySettings[index]["CandleInterval"] = request.form.get("CandleInterval")
                strategySettings[index]["NumOfCandlesForLookback"] = int(request.form.get("NumOfCandlesForLookback"))
                strategySettings[index]["timeLimitNewOrder"] = int(request.form.get("timeLimitNewOrder"))
                #Asset manager
                strategySettings[index]["assetManagerTarget"] = request.form.get("assetManagerTarget") #Type of asset managment string
                strategySettings[index]["assetManagerSymbol"] = int(request.form.get("assetManagerSymbol"))
                strategySettings[index]["assetManageMaxSpendLimit"] = float(request.form.get("assetManageMaxSpendLimit"))
                strategySettings[index]["assetManageMinSaveLimit"] = float(request.form.get("assetManageMinSaveLimit"))
                strategySettings[index]["assetManagePercent"] = int(request.form.get("assetManagePercent")) 

                strategySettings[index]["roundBuySellorder"] = int(request.form.get("roundBuySellorder"))
                strategySettings[index]["BuyBase"] = float(request.form.get("BuyBase"))
                strategySettings[index]["BuyMin"] = float(request.form.get("BuyMin"))
                strategySettings[index]["DipBuy"] = float(request.form.get("DipBuy"))
                strategySettings[index]["BuyMaxFactor"] = float(request.form.get("BuyMaxFactor"))
                strategySettings[index]["MinWeight_Buy"] = int(request.form.get("MinWeight_Buy"))
                strategySettings[index]["MinWeight_Sell"] = int(request.form.get("MinWeight_Sell"))
                strategySettings[index]["SellBase"] = float(request.form.get("SellBase"))
                strategySettings[index]["SellMin"] = float(request.form.get("SellMin"))
                strategySettings[index]["TakeProfit"] = float(request.form.get("TakeProfit"))
                strategySettings[index]["SellMaxFactor"] = float(request.form.get("SellMaxFactor"))
                #START DynamicBuy stting saved-----------------------------------------------------------------------------------
                strategySettings[index]["DynamicBuy"] = []
                for i,_ in enumerate(request.form.getlist("DynamicBuyType")): 
                    if len(strategySettings[index]["DynamicBuy"]) < len(request.form.getlist("DynamicBuyType")):
                        strategySettings[index]["DynamicBuy"].append({})
                    strategySettings[index]["DynamicBuy"][i]["Type"] = request.form.getlist("DynamicBuyType")[i]
                    strategySettings[index]["DynamicBuy"][i]["Interval"] = request.form.getlist("DynamicBuyInterval")[i]
                    if int(request.form.getlist("DynamicBuyEnable")[i]) == 0:
                        strategySettings[index]["DynamicBuy"][i]["Enable"] = False
                    else:
                        strategySettings[index]["DynamicBuy"][i]["Enable"] = True
                    
                    strategySettings[index]["DynamicBuy"][i]["Weight"] = int(request.form.getlist("DynamicBuyWeight")[i])
                    strategySettings[index]["DynamicBuy"][i]["BlockTradeOffset"] = float(request.form.getlist("DynamicBuyBlockTradeOffset")[i])
                    strategySettings[index]["DynamicBuy"][i]["Value"] = int(request.form.getlist("DynamicBuyValue")[i])
                    strategySettings[index]["DynamicBuy"][i]["Value2"] = int(request.form.getlist("DynamicBuyValue2")[i])
                    strategySettings[index]["DynamicBuy"][i]["Value3"] = int(request.form.getlist("DynamicBuyValue3")[i])
                    strategySettings[index]["DynamicBuy"][i]["Value4"] = int(request.form.getlist("DynamicBuyValue4")[i])
                    strategySettings[index]["DynamicBuy"][i]["OutputSelect"] = request.form.getlist("DynamicBuyOutputSelect")[i]
                    strategySettings[index]["DynamicBuy"][i]["Comparator"] = request.form.getlist("DynamicBuyComparator")[i]
                    strategySettings[index]["DynamicBuy"][i]["Trigger"] = float(request.form.getlist("DynamicBuyTrigger")[i])              
                    strategySettings[index]["DynamicBuy"][i]["TriggerSelect"] = request.form.getlist("DynamicBuyTriggerSelect")[i]
                    strategySettings[index]["DynamicBuy"][i]["Factor"] = float(request.form.getlist("DynamicBuyFactor")[i])
                    strategySettings[index]["DynamicBuy"][i]["Max"] = float(request.form.getlist("DynamicBuyMax")[i])
                #START dynamicSell stting saved-----------------------------------------------------------------------------------
                strategySettings[index]["DynamicSell"] = []
                for i,_ in enumerate(request.form.getlist("DynamicSellType")):    
                    if len(strategySettings[index]["DynamicSell"]) < len(request.form.getlist("DynamicSellType")):
                        strategySettings[index]["DynamicSell"].append({})
                    strategySettings[index]["DynamicSell"][i]["Type"] = request.form.getlist("DynamicSellType")[i]
                    strategySettings[index]["DynamicSell"][i]["Interval"] = request.form.getlist("DynamicSellInterval")[i]
                    if int(request.form.getlist("DynamicSellEnable")[i]) == 0:
                        strategySettings[index]["DynamicSell"][i]["Enable"] = False
                    else:
                        strategySettings[index]["DynamicSell"][i]["Enable"] = True
                        
                    strategySettings[index]["DynamicSell"][i]["Weight"] = int(request.form.getlist("DynamicSellWeight")[i])
                    strategySettings[index]["DynamicSell"][i]["BlockTradeOffset"] = float(request.form.getlist("DynamicSellBlockTradeOffset")[i])
                    strategySettings[index]["DynamicSell"][i]["Value"] = int(request.form.getlist("DynamicSellValue")[i])
                    strategySettings[index]["DynamicSell"][i]["Value2"] = int(request.form.getlist("DynamicSellValue2")[i])
                    strategySettings[index]["DynamicSell"][i]["Value3"] = int(request.form.getlist("DynamicSellValue3")[i])
                    strategySettings[index]["DynamicSell"][i]["Value4"] = int(request.form.getlist("DynamicSellValue4")[i])
                    strategySettings[index]["DynamicSell"][i]["OutputSelect"] = request.form.getlist("DynamicSellOutputSelect")[i]
                    strategySettings[index]["DynamicSell"][i]["Comparator"] = request.form.getlist("DynamicSellComparator")[i]
                    strategySettings[index]["DynamicSell"][i]["Trigger"] = float(request.form.getlist("DynamicSellTrigger")[i])      
                    strategySettings[index]["DynamicSell"][i]["TriggerSelect"] = request.form.getlist("DynamicSellTriggerSelect")[i]
                    strategySettings[index]["DynamicSell"][i]["Factor"] = float(request.form.getlist("DynamicSellFactor")[i])
                    strategySettings[index]["DynamicSell"][i]["Max"] = float(request.form.getlist("DynamicSellMax")[i])
            
                saveStrSettings(strategySettings)
                scrollId = strategySettings[index]["id"]
                #flash('data saved succesfuly', 'success')
            else:
                #usrMsg=f"error"
                print(f"Addbuton---{usrMsg}-----{request.form.get("ActionButton")}")
        except Exception as e:
            print(f"strategySettings.html error: {e}")
    
    return render_template('strategySettings.html',
                        AllStrategySettings = strategySettings,
                        timeAppRunning=passToFlask["timeAppRunning"],
                        scrollId=scrollId,
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usrMsg,
                        fearAndGreed=fearAndGreed,
                        activStreamList=activStreamList
                        )


@bp.route("/BasicSettings", methods=['GET', 'POST'])
@login_required
def BasicSettings(): 
    usrMsg=""
    data = ""
    basicSettings = loadBsettings()
    if request.method == 'POST' and request.form:      
        if "SAVE" == request.form.get("ActionButton"):
            basicSettings["histDataUpdate"] = int(request.form.get("histDataUpdate")) 
            basicSettings["strategyUpdate"] = int(request.form.get("strategyUpdate")) 
            basicSettings["liveTradeAging"] = int(request.form.get("liveTradeAging")) 
            basicSettings["numOfHisCandles"] = int(request.form.get("numOfHisCandles")) 
            basicSettings["pingUpdate"] = int(request.form.get("pingUpdate")) 
            basicSettings["klineStreamLoopRuntime"] = float(request.form.get("klineStreamLoopRuntime")) 
            basicSettings["websocetManageLoopRuntime"] = float(request.form.get("websocetManageLoopRuntime"))       
            basicSettings["timeout"] = int(request.form.get("timeout")) 
            basicSettings["reconnect_delay"] = int(request.form.get("reconnect_delay")) 
            basicSettings["host"] = request.form.get("host")
            basicSettings["Port"] = int(request.form.get("Port"))
            basicSettings["user"] = request.form.get("user")
            basicSettings["password"] = request.form.get("password")
            basicSettings["API_KEY"] = request.form.get("API_KEY")
            basicSettings["API_SECRET"] = request.form.get("API_SECRET")
            if request.form.get("useTelegram") == None:
                basicSettings["useTelegram"] = False
            else:
                basicSettings["useTelegram"] = True
            basicSettings["telegram_TOKEN"] = request.form.get("telegram_TOKEN")
            basicSettings["telegram_chatID"] = request.form.get("telegram_chatID")
            saveBsettings(basicSettings)
            usrMsg=f"Basic settings were succesfuly SAVED"

    return render_template("BasicSettings.html",
                        my_basicSettings = basicSettings,
                        timeAppRunning=passToFlask["timeAppRunning"],
                        pingResponse=passToFlask["conManageResponse"],
                        usrMsg=usrMsg,
                        data = data,
                        activStreamList=activStreamList,
                        fearAndGreed=fearAndGreed,
                        exchange_info_data = exchange_info_data
                        )
