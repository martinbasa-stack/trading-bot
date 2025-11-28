def extract_strategy_from_form(request):
    #Convert HTML form fields into a clean strategy dict
    data = {
        "name": request.form.get("name"),
        "type": "AdvancedDCA",
        "Symbol1": request.form.get("Symbol1"),
        "Symbol2": request.form.get("Symbol2"),
        "run": bool(request.form.get("run")),
        "paperTrading": bool(request.form.get("paperTrading")),
        "candleCloseOnly": bool(request.form.get("candleCloseOnly")),
        "CandleInterval": request.form.get("CandleInterval"),
        "NumOfCandlesForLookback": int(request.form.get("NumOfCandlesForLookback")),
        "timeLimitNewOrder": int(request.form.get("timeLimitNewOrder")),

        # Asset manager
        "assetManagerTarget": request.form.get("assetManagerTarget"),
        "assetManagerSymbol": int(request.form.get("assetManagerSymbol")),
        "assetManageMaxSpendLimit": float(request.form.get("assetManageMaxSpendLimit")),
        "assetManageMinSaveLimit": float(request.form.get("assetManageMinSaveLimit")),
        "assetManagePercent": int(request.form.get("assetManagePercent")),

        # Basic buy/sell
        "roundBuySellorder": int(request.form.get("roundBuySellorder")),
        "BuyBase": float(request.form.get("BuyBase")),
        "BuyMin": float(request.form.get("BuyMin")),
        "DipBuy": float(request.form.get("DipBuy")),
        "BuyMaxFactor": float(request.form.get("BuyMaxFactor")),
        "MinWeight_Buy": int(request.form.get("MinWeight_Buy")),
        "MinWeight_Sell": int(request.form.get("MinWeight_Sell")),
        "SellBase": float(request.form.get("SellBase")),
        "SellMin": float(request.form.get("SellMin")),
        "TakeProfit": float(request.form.get("TakeProfit")),
        "SellMaxFactor": float(request.form.get("SellMaxFactor")),
    }

    # -------------------------
    # Dynamic Buy
    # -------------------------
    dyn_buy = []
    count = len(request.form.getlist("DynamicBuyType"))
    for i in range(count):
        dyn_buy.append({
            "Type": request.form.getlist("DynamicBuyType")[i],
            "Interval": request.form.getlist("DynamicBuyInterval")[i],
            "Enable": bool(int(request.form.getlist("DynamicBuyEnable")[i])),
            "Weight": int(request.form.getlist("DynamicBuyWeight")[i]),
            "BlockTradeOffset": float(request.form.getlist("DynamicBuyBlockTradeOffset")[i]),
            "Value": int(request.form.getlist("DynamicBuyValue")[i]),
            "Value2": int(request.form.getlist("DynamicBuyValue2")[i]),
            "Value3": int(request.form.getlist("DynamicBuyValue3")[i]),
            "Value4": int(request.form.getlist("DynamicBuyValue4")[i]),
            "OutputSelect": request.form.getlist("DynamicBuyOutputSelect")[i],
            "Comparator": request.form.getlist("DynamicBuyComparator")[i],
            "Trigger": float(request.form.getlist("DynamicBuyTrigger")[i]),
            "TriggerSelect": request.form.getlist("DynamicBuyTriggerSelect")[i],
            "Factor": float(request.form.getlist("DynamicBuyFactor")[i]),
            "Max": float(request.form.getlist("DynamicBuyMax")[i])
        })
    data["DynamicBuy"] = dyn_buy

    # -------------------------
    # Dynamic Sell
    # -------------------------
    dyn_sell = []
    count = len(request.form.getlist("DynamicSellType"))
    for i in range(count):
        dyn_sell.append({
            "Type": request.form.getlist("DynamicSellType")[i],
            "Interval": request.form.getlist("DynamicSellInterval")[i],
            "Enable": bool(int(request.form.getlist("DynamicSellEnable")[i])),
            "Weight": int(request.form.getlist("DynamicSellWeight")[i]),
            "BlockTradeOffset": float(request.form.getlist("DynamicSellBlockTradeOffset")[i]),
            "Value": int(request.form.getlist("DynamicSellValue")[i]),
            "Value2": int(request.form.getlist("DynamicSellValue2")[i]),
            "Value3": int(request.form.getlist("DynamicSellValue3")[i]),
            "Value4": int(request.form.getlist("DynamicSellValue4")[i]),
            "OutputSelect": request.form.getlist("DynamicSellOutputSelect")[i],
            "Comparator": request.form.getlist("DynamicSellComparator")[i],
            "Trigger": float(request.form.getlist("DynamicSellTrigger")[i]),
            "TriggerSelect": request.form.getlist("DynamicSellTriggerSelect")[i],
            "Factor": float(request.form.getlist("DynamicSellFactor")[i]),
            "Max": float(request.form.getlist("DynamicSellMax")[i])
        })
    data["DynamicSell"] = dyn_sell

    return data

def extract_settings_from_form(request):
    data = {
        "histDataUpdate" : int(request.form.get("histDataUpdate")),
        "strategyUpdate" : int(request.form.get("strategyUpdate")),
        "liveTradeAging" : int(request.form.get("liveTradeAging")),
        "numOfHisCandles" : int(request.form.get("numOfHisCandles")),
        "pingUpdate" : int(request.form.get("pingUpdate")),
        "klineStreamLoopRuntime" : float(request.form.get("klineStreamLoopRuntime")), 
        "websocetManageLoopRuntime" : float(request.form.get("websocetManageLoopRuntime")),
        "timeout" : int(request.form.get("timeout")),
        "reconnect_delay" : int(request.form.get("reconnect_delay")),
        "host" : request.form.get("host"),
        "Port" : int(request.form.get("Port")),
        "user" : request.form.get("user"),
        "password" : request.form.get("password"),
        "API_KEY" : request.form.get("API_KEY"),
        "API_SECRET" : request.form.get("API_SECRET"),
        "useTelegram" : bool(request.form.get("useTelegram")),
        "telegram_TOKEN" : request.form.get("telegram_TOKEN"),
        "telegram_chatID" : request.form.get("telegram_chatID")
    }
    return data