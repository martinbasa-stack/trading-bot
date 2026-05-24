from .models import StrategyConfig, AssetManagerConfig, IndicatorConfig

# Helper converters to from DataClass and dict for savin and loading to .json
# ----------------------------------------------------------------------
def dict_to_indicator(d: dict) -> IndicatorConfig:
    return IndicatorConfig(
        type_i=d["Type"],
        interval=d["Interval"],
        enable=d["Enable"],
        weight=d["Weight"],
        block_trade_offset=d["BlockTradeOffset"],
        value1=d["Value"],
        value2=d["Value2"],
        value3=d["Value3"],
        value4=d["Value4"],
        output_select=d["OutputSelect"],
        comparator=d["Comparator"],
        trigger=d["Trigger"],
        trigger_select=d["TriggerSelect"],
        factor=d["Factor"],
        max_f=d["Max"],
    )


def indicator_to_dict(i: IndicatorConfig) -> dict:
    return {
        "Type": i.type_i,
        "Interval": i.interval,
        "Enable": i.enable,
        "Weight": i.weight,
        "BlockTradeOffset": i.block_trade_offset,
        "Value": i.value1,
        "Value2": i.value2,
        "Value3": i.value3,
        "Value4": i.value4,
        "OutputSelect": i.output_select,
        "Comparator": i.comparator,
        "Trigger": i.trigger,
        "TriggerSelect": i.trigger_select,
        "Factor": i.factor,
        "Max": i.max_f,
    }


def dict_to_asset_manager(d: dict) -> AssetManagerConfig:
    return AssetManagerConfig(
        target=d["assetManagerTarget"],
        symbol_index=d["assetManagerSymbol"],
        max_spend_limit=d["assetManageMaxSpendLimit"],
        min_save_limit=d["assetManageMinSaveLimit"],
        percent=d["assetManagePercent"],
        paper_t=d["paperTrading"],

        buy_base=d["BuyBase"],
        buy_min=d["BuyMin"],
        dip_buy=d["DipBuy"],
        buy_max_factor=d["BuyMaxFactor"],
        min_weight_buy=d["MinWeight_Buy"],

        sell_base=d["SellBase"],
        sell_min=d["SellMin"],
        pump_sell=d["PumpSell"],
        sell_max_factor=d["SellMaxFactor"],
        min_weight_sell=d["MinWeight_Sell"],
    )


def asset_manager_to_dict(a: AssetManagerConfig) -> dict:
    return {
        "assetManagerTarget": a.target,
        "assetManagerSymbol": a.symbol_index,
        "assetManageMaxSpendLimit": a.max_spend_limit,
        "assetManageMinSaveLimit": a.min_save_limit,
        "assetManagePercent": a.percent,
        "paperTrading": a.paper_t,

        "BuyBase": a.buy_base,
        "BuyMin": a.buy_min,
        "DipBuy": a.dip_buy,
        "BuyMaxFactor": a.buy_max_factor,
        "MinWeight_Buy": a.min_weight_buy,

        "SellBase": a.sell_base,
        "SellMin": a.sell_min,
        "PumpSell": a.pump_sell,
        "SellMaxFactor": a.sell_max_factor,
        "MinWeight_Sell": a.min_weight_sell,
    }


def dict_to_strategy(d: dict) -> StrategyConfig:
    am = dict_to_asset_manager(d)

    dyn_buy = [dict_to_indicator(x) for x in d.get("DynamicBuy", [])]
    dyn_sell = [dict_to_indicator(x) for x in d.get("DynamicSell", [])]

    return StrategyConfig(
        name=d["name"],
        type_s=d["type"],
        symbol1=d["Symbol1"],
        symbol2=d["Symbol2"],
        run=d["run"],
        candle_close_only=d["candleCloseOnly"],
        last_trade_as_min_max=d["useLastTradeAsMinMax"],
        candle_interval=d["CandleInterval"],
        lookback=d["NumOfCandlesForLookback"],
        time_limit_new_order=d["timeLimitNewOrder"],
        round_order=d["roundBuySellorder"],
        idx=d["id"],
        asset_manager=am,
        indicators_buy=dyn_buy,
        indicators_sell=dyn_sell
    )


def strategy_to_dict(s: StrategyConfig) -> dict:
    return {
        "name": s.name,
        "type": s.type_s,
        "Symbol1": s.symbol1,
        "Symbol2": s.symbol2,
        "run": s.run,
        "candleCloseOnly": s.candle_close_only,
        "useLastTradeAsMinMax": s.last_trade_as_min_max,
        "CandleInterval": s.candle_interval,
        "NumOfCandlesForLookback": s.lookback,
        "timeLimitNewOrder": s.time_limit_new_order,
        "roundBuySellorder": s.round_order,
        "id": s.idx,
        **asset_manager_to_dict(s.asset_manager),
        "DynamicBuy": [indicator_to_dict(i) for i in s.indicators_buy],
        "DynamicSell": [indicator_to_dict(i) for i in s.indicators_sell],
    }