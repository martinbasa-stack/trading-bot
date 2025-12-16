from src.settings import StrategyConfig, IndicatorConfig, AssetManagerConfig

import logging

# Get logger
logger = logging.getLogger(__name__)

def extract_strategy_from_form(request) -> StrategyConfig:
    """
    Helper for building StrategyConfig
    Returns:
        StrategyConfig:
            DataClass to serve to the StrategyManager
    """
    try:
        # -------------------------
        # Build AssetManagerConfig
        # -------------------------
        asset_manager = AssetManagerConfig(
            target=request.form.get("assetManagerTarget"),
            symbol_index=int(request.form.get("assetManagerSymbol")),
            max_spend_limit=float(request.form.get("assetManageMaxSpendLimit")),
            min_save_limit=float(request.form.get("assetManageMinSaveLimit")),
            percent=float(request.form.get("assetManagePercent")),
            paper_t=bool(request.form.get("paperTrading")),

            # Buy parameters
            buy_base=float(request.form.get("BuyBase")),
            buy_min=float(request.form.get("BuyMin")),
            dip_buy=float(request.form.get("DipBuy")),
            buy_max_factor=float(request.form.get("BuyMaxFactor")),
            min_weight_buy=int(request.form.get("MinWeight_Buy")),

            # Sell parameters
            sell_base=float(request.form.get("SellBase")),
            sell_min=float(request.form.get("SellMin")),
            pump_sell=float(request.form.get("PumpSell")),
            sell_max_factor=float(request.form.get("SellMaxFactor")),
            min_weight_sell=int(request.form.get("MinWeight_Sell")),
        )

        # -------------------------
        # Build Dynamic BUY indicators
        # -------------------------
        indicators_buy = []
        count = len(request.form.getlist("DynamicBuyType"))
        for i in range(count):
            indicators_buy.append(
                IndicatorConfig(
                    type_i=request.form.getlist("DynamicBuyType")[i],
                    interval=request.form.getlist("DynamicBuyInterval")[i],
                    enable=bool(int(request.form.getlist("DynamicBuyEnable")[i])),
                    weight=int(request.form.getlist("DynamicBuyWeight")[i]),
                    block_trade_offset=float(request.form.getlist("DynamicBuyBlockTradeOffset")[i]),
                    value1=int(request.form.getlist("DynamicBuyValue")[i]),
                    value2=int(request.form.getlist("DynamicBuyValue2")[i]),
                    value3=int(request.form.getlist("DynamicBuyValue3")[i]),
                    value4=int(request.form.getlist("DynamicBuyValue4")[i]),
                    output_select=request.form.getlist("DynamicBuyOutputSelect")[i],
                    comparator=request.form.getlist("DynamicBuyComparator")[i],
                    trigger=float(request.form.getlist("DynamicBuyTrigger")[i]),
                    trigger_select=request.form.getlist("DynamicBuyTriggerSelect")[i],
                    factor=float(request.form.getlist("DynamicBuyFactor")[i]),
                    max_f=float(request.form.getlist("DynamicBuyMax")[i]),
                )
            )

        # -------------------------
        # Build Dynamic SELL indicators
        # -------------------------
        indicators_sell = []
        count = len(request.form.getlist("DynamicSellType"))
        for i in range(count):
            indicators_sell.append(
                IndicatorConfig(
                    type_i=request.form.getlist("DynamicSellType")[i],
                    interval=request.form.getlist("DynamicSellInterval")[i],
                    enable=bool(int(request.form.getlist("DynamicSellEnable")[i])),
                    weight=int(request.form.getlist("DynamicSellWeight")[i]),
                    block_trade_offset=float(request.form.getlist("DynamicSellBlockTradeOffset")[i]),
                    value1=int(request.form.getlist("DynamicSellValue")[i]),
                    value2=int(request.form.getlist("DynamicSellValue2")[i]),
                    value3=int(request.form.getlist("DynamicSellValue3")[i]),
                    value4=int(request.form.getlist("DynamicSellValue4")[i]),
                    output_select=request.form.getlist("DynamicSellOutputSelect")[i],
                    comparator=request.form.getlist("DynamicSellComparator")[i],
                    trigger=float(request.form.getlist("DynamicSellTrigger")[i]),
                    trigger_select=request.form.getlist("DynamicSellTriggerSelect")[i],
                    factor=float(request.form.getlist("DynamicSellFactor")[i]),
                    max_f=float(request.form.getlist("DynamicSellMax")[i]),
                )
            )

        # -------------------------
        # Build StrategyConfig root
        # -------------------------
        strategy = StrategyConfig(
            name=request.form.get("name"),
            type_s="AdvancedDCA",
            symbol1=request.form.get("Symbol1"),
            symbol2=request.form.get("Symbol2"),
            run=bool(request.form.get("run")),
            candle_close_only=bool(request.form.get("candleCloseOnly")),
            last_trade_as_min_max=bool(request.form.get("useLastTradeAsMinMax")),
            candle_interval=request.form.get("CandleInterval"),
            lookback=int(request.form.get("NumOfCandlesForLookback")),
            time_limit_new_order=int(request.form.get("timeLimitNewOrder")),
            round_order=int(request.form.get("roundBuySellorder")),
            idx=-1,  # StrategyManager will overwrite this when adding

            asset_manager=asset_manager,
            indicators_buy=indicators_buy,
            indicators_sell=indicators_sell,
        )

        return strategy
    except Exception as e:
        logger.error(f"extract_strategy_from_form() error: {e}")

def extract_settings_from_form(request) -> dict:
    """
    Helper for building dict
    Returns:
        dict:
            Dictionary to serve to the SettingsMannager
    """
    try:
        data = {
            "histDataUpdate" : int(request.form.get("histDataUpdate")),
            "strategyUpdate" : int(request.form.get("strategyUpdate")),
            "liveTradeAging" : int(request.form.get("liveTradeAging")),
            "numOfHisCandles" : int(request.form.get("numOfHisCandles")),
            "pingUpdate" : int(request.form.get("pingUpdate")),
            "statusUpdate" : int(request.form.get("statusUpdate")),
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
    except Exception as e:
        logger.error(f"extract_settings_from_form() error: {e}")