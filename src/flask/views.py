from src.settings import settings_obj, strategies_obj, IndicatorConfig
from src.market_history import market_history_obj, fear_gread_obj
from src.strategy import trade_manager_obj, asset_manager_obj, TradeAnalyzer, AssetAnalyzer, AssetManagerResult, AverageSum, Balance
from src.strategy.indicators import IndicatorCompute, IndicatorResult
from src.binance import stream_manager_obj
from src.strategy.run import  record_obj
from src.strategy.dca import DCAstrategy , TriggerComputeResult
from src.binance import ws_manager_obj
from src.constants import LOG_PATH_STRATEGY

from datetime import datetime, timezone, timedelta
import logging

# Get logger
logger = logging.getLogger(__name__)

BOT_VERSION = "V1.4"

def _now():    
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp()) 

app_start = _now()

def _find_round(val: float, min_dec:int =2) -> int:
    """
    Return rounded value with auto adjustable decimal places in order to not display 0

    Args:
        val(float):
            Value you want to round

        min_dec(int, optional):
            Minimum decimal places to round.
    
    Returns:
        int: Number of decimal places to rount the value to.
    """
    temp = val
    count_round = min_dec
    while temp < 1 and temp > 0:
        temp = temp*10
        count_round +=1  
    return count_round

def footer_text() -> dict:
    """
    Returns:
        dict:
            Data for Flask
    """
    try:
        now_seconds = _now()    
        text_first = ws_manager_obj.get_last_ping_resp()    
        
        text_first = (f"Bot {BOT_VERSION} Startup at {datetime.fromtimestamp(app_start)} | running for {timedelta(seconds = now_seconds - app_start)}"
                f" Last server response: {text_first}"
                )

        #Missing ping response after proper object is constructed for websocets cmds
        fear_gread = fear_gread_obj.get_full()
        time_new_data= int(fear_gread.timestamp) + int(fear_gread.time_until_update) +60
        text_second = (
                f"Active streams: {stream_manager_obj.get_active_list()}  |  "
                f"Fear & Gread: {fear_gread.value} Class: {fear_gread.value_classification} New data at: {datetime.fromtimestamp(time_new_data)}"
                )
        return {"first": text_first, "second":text_second }
    
    except Exception as e:
        logger.error(f"footer_text() error: {e}")

def strategy_list() -> list[dict]:
    """
    Returns:
        dict:
            Data for Flask
    """
    try:
        list_names = []     
        
        id_list = strategies_obj.get_id_list()
        for idx in id_list:
            if idx == "backtester":
                continue            
            s = strategies_obj.get_by_id(idx)
            p=""
            if s.asset_manager.paper_t:
                p = "p"
                
            name= f"{p} {s.symbol1}/{s.symbol2} {s.candle_interval}"
            list_names.append({
                "idx" : idx,
                "name" : name
            })        
        return list_names
    
    except Exception as e:
        logger.error(f"strategy_list() error: {e}")

def assets_view() -> dict:
    """
    Returns:
        dict:
            Data for Flask
    """
    try:
        asset_list: dict[Balance] = asset_manager_obj.get_all()
        view = {}
        for key, asset in asset_list.items():
            view[key] = {
                "Available" : asset.available,            
                "Total" : asset.total,
                "Locked" : asset.locked
            }
        return view
    except Exception as e:
        logger.error(f"assets_view() error: {e}")

def trade_table_view() -> dict:
    """
    Returns:
        dict:
            Data for Flask
    """
    try:
        view = {} #Cleare the whole table before creating
        
        for idx in strategies_obj.get_id_list():
            trade_table = trade_manager_obj.get_table(idx)    
            if trade_table is None:
                continue
            strategy = strategies_obj.get_by_id(idx)
            if strategy is None:
                continue 
            table_view = []
            reversed_arr  = trade_table[::-1]#Reorder from new to old new at the top
            for i in reversed_arr:   # Formating of timestamp and converting all to string since it is only for display
                tempTupple = (
                str(datetime.fromtimestamp(int(i.timestamp/1000))), 
                str(i.idx),
                str(i.symbol1),
                float(i.quantity1),
                str(i.symbol2),
                float(i.quantity2),
                float(i.price),
                str(round(i.change,2)),
                str(i.commision),
                str(i.commision_symbol)
                )       
                table_view.append(tempTupple)  

            if not table_view: #If empty write a defaule empty tuple for template rendering
                table_view = [(0,"Empty","Symbol1",0,"Symbol2",0,0,0,0,"SymbolC")] 
            view[idx] = {} # initiate / if exist it will cleare the strategy trade data
            #Fill base data
            s1 = strategy.symbol1
            s2 = strategy.symbol2
            view[idx]["Symbol1"] = s1
            view[idx]["Symbol2"] = s2
            view[idx]["CandleInterval"] = strategy.candle_interval
            view[idx]["type"] = strategy.type_s
            view[idx]["paperTrading"] = strategy.asset_manager.paper_t
            view[idx]["name"] = f"{strategy.name}_{s1}_{s2}"
            view[idx]["trades"] = table_view
        
        return view
    except Exception as e:
        logger.error(f"trade_table_view() error: {e}")

def strategy_status_view() -> dict:
    """
    Returns:
        dict:
            Data for Flask
    """
    try:
        view = {} #Create the dict display

        # short lived objec declarations
        trade_analyzer_obj = TradeAnalyzer(get_trade_table=trade_manager_obj.get_table,
                                    get_hist_table=market_history_obj.get_table,
                                    get_by_id=strategies_obj.get_by_id
                                    )
        indicators_obj =IndicatorCompute(
            strategies_obj=strategies_obj,
            get_all_avg=trade_analyzer_obj.get_all_avgs,
            get_hist_table=market_history_obj.get_table,
            get_close=stream_manager_obj.get_close,
            fear_gread_get=fear_gread_obj.get
            )
        asset_analyzer_obj = AssetAnalyzer(
            get_by_id=strategies_obj.get_by_id,
            get_all_avg=trade_analyzer_obj.get_all_avgs,
            get_available_balance=asset_manager_obj.get_available,
            get_close=stream_manager_obj.get_close
        )

        dac_strategy = DCAstrategy(
            strategies_obj=strategies_obj,
            trade_analyzer_obj = trade_analyzer_obj,
            indicators_obj = indicators_obj,
            asset_analyzer_obj = asset_analyzer_obj,
            stream_get_close = stream_manager_obj.get_close,
            record_obj = record_obj 
        )

        for idx in strategies_obj.get_id_list():
            strategy = strategies_obj.get_by_id(idx)
            s1 = strategy.symbol1
            s2 = strategy.symbol2
            pair = f"{s1}{s2}"
            view_idx = {}
            #Update price data 
            new_close = stream_manager_obj.get_close(pair) 

            # Get min max price
            avg_entry, avg_cost, avg_exit = trade_analyzer_obj.get_all_avgs(idx)
            pnl = trade_analyzer_obj.get_pnl(idx, new_close)

            #Compute indicator values
            dca_result : TriggerComputeResult = dac_strategy.get_trigger_compute(idx)
            if not dca_result:
                return view_idx
            #Asset managment
            asset_resault : AssetManagerResult = asset_analyzer_obj.get_compute(idx, dca_result.buy_factor, dca_result.sell_factor) 
        

            s1_round = _find_round(asset_resault.to_sell/new_close)     
            #Save strategy values 
            view_idx["last_price"] = round(new_close, _find_round(new_close))

            view_idx["cost_avg"] = round(avg_cost.avg, strategy.round_order)
            view_idx["cost_sum1"] = round(avg_cost.sum1, s1_round)
            view_idx["cost_sum2"] = round(avg_cost.sum2, strategy.round_order)
            view_idx["cost_num"] = avg_cost.num

            view_idx["entry_avg"] = round(avg_entry.avg, strategy.round_order)
            view_idx["entry_sum1"] = round(avg_entry.sum1, s1_round)
            view_idx["entry_sum2"] = round(avg_entry.sum2, strategy.round_order)
            view_idx["entry_num"] = avg_entry.num

            view_idx["exit_avg"] = round(avg_exit.avg, strategy.round_order)
            view_idx["exit_sum1"] = round(avg_exit.sum1, s1_round)
            view_idx["exit_sum2"] = round(avg_exit.sum2, strategy.round_order)
            view_idx["exit_num"] = avg_exit.num

            view_idx["pnl_total"] = round(pnl.total, strategy.round_order)
            view_idx["pnl_total_percent"] = round(pnl.total_percent, 2)
            view_idx["pnl_realized"] = round(pnl.realised, strategy.round_order)
            view_idx["pnl_realized_percent"] = round(pnl.real_percent, 2)
            view_idx["pnl_unrealized"] = round(pnl.unrealised, strategy.round_order)
            view_idx["pnl_unrealized_percent"] = round(pnl.unreal_percent, 2)

            view_idx["max_price"] = dca_result.max_price
            view_idx["min_price"] = dca_result.min_price
            view_idx["lookback"] = dca_result.lookback

            view_idx["start_time"] = datetime.fromtimestamp(trade_manager_obj.get_first_timestamp(idx))
                
            view_idx["symbol1"] = s1
            view_idx["symbol2"] = s2
            view_idx["candle_close_only"] = strategy.candle_close_only
            view_idx["candle_interval"] = strategy.candle_interval
            view_idx["type"] = strategy.type_s
            view_idx["name"] = f"{strategy.name} ID:{idx} {s1}/{s2}"

            view_idx["buy_base"] = strategy.asset_manager.buy_base
            view_idx["buy_min"] = strategy.asset_manager.buy_min
            view_idx["sell_base"] = strategy.asset_manager.sell_base
            view_idx["sell_min"] = strategy.asset_manager.sell_min
            view_idx["paper_trading"] = strategy.asset_manager.paper_t

            if strategy.asset_manager.symbol_index ==1:
                am_symbol = s1
            else:
                am_symbol = s2
            view_idx["am_symbol"] = am_symbol
            view_idx["am_target"] = strategy.asset_manager.target
            view_idx["am_available_s2"] = round(asset_resault.available_s2, strategy.round_order)
            view_idx["am_available_s1"] = round(asset_resault.available_s1, s1_round)
            view_idx["balance_s2"] = round(asset_manager_obj.get_available(s2), strategy.round_order)
            view_idx["balance_s1"] = round(asset_manager_obj.get_available(s1), s1_round)

            view_idx["trade_enable"] = dca_result.trade_enable

            view_idx["buy_dca_trigger"] = dca_result.dca_buy_trigger
            view_idx["buy_ind_en"] = dca_result.buy_ind_trade_en
            view_idx["buy_balance_ok"] = asset_resault.s2_balance_ok
            view_idx["min_weight_buy"] = strategy.asset_manager.min_weight_buy
            view_idx["buy_weight"] = dca_result.buy_weight
            view_idx["to_buy_s1"] = round(asset_resault.to_buy/new_close, s1_round)
            view_idx["to_buy_s2"] = round(asset_resault.to_buy, strategy.round_order)
            view_idx["buy_factor"] =  round(dca_result.buy_factor,2) 
            view_idx["buy_percent_change_dip"] = round(dca_result.percent_change_dip,2)

            view_idx["sell_dca_trigger"] = dca_result.dca_sell_trigger
            view_idx["sell_balance_ok"] = asset_resault.s1_balance_ok
            view_idx["sell_ind_en"] = dca_result.sell_ind_trade_en
            view_idx["min_weight_sell"] = strategy.asset_manager.min_weight_sell
            view_idx["sell_weight"] = dca_result.sell_weight 
            view_idx["sell_percent_change_pump"] = round(dca_result.percent_change_pump,2)
            view_idx["to_sell_s1"] = round(asset_resault.to_sell/new_close, s1_round)
            view_idx["to_sell_s2"] = round(asset_resault.to_sell, strategy.round_order)
            view_idx["sell_factor"] = round(dca_result.sell_factor,2) 

            view_ind_buy = _indicators_view(strategy.indicators_buy, indicators_obj.get_buy_list(idx), strategy.round_order)
            if not view_ind_buy:
                view_ind_buy = _empty_indicator

            view_idx["view_ind_buy"] = view_ind_buy

            view_ind_sell = _indicators_view(strategy.indicators_sell, indicators_obj.get_sell_list(idx), strategy.round_order)
            if not view_ind_sell:
                view_ind_sell = _empty_indicator

            view_idx["view_ind_sell"] = view_ind_sell
            
            view[idx] = view_idx

        return view    
    except Exception as e:
            logger.error(f"strategy_status_view() error: {e}")

def _indicators_view(indic_config: list[IndicatorConfig], indic_result: list[IndicatorResult], round_order) -> list[dict]:
    view_list = []
    for idx, config in enumerate(indic_config):
        view_ind = {}
        result = indic_result[idx]

        
        view_ind["idx"]= idx
        view_ind["type"]= config.type_i
        view_ind["interval"]= config.interval
        view_ind["enable"]= config.enable
        view_ind["weight_config"]= config.weight
        view_ind["comparator"]= config.comparator
        view_ind["value1"]= config.value1
        view_ind["value2"]= config.value2
        view_ind["value3"]= config.value3
        view_ind["value4"]= config.value4

        view_ind["enable_trade"]= result.enable_trade
        view_ind["val_to_comare"]= round(result.out_val,_find_round(result.out_val))
        view_ind["weight_result"]= result.weight
        view_ind["delta"]= round(result.delta,2)
        view_ind["factor"]= round(result.factor,2)
        view_ind["factor_limit"]= round(result.factor_limit,2)
        view_ind["dis_text"]= result.dis_text
        view_ind["trigger"]= round(result.trigger, round_order)   
        view_ind["trigger_offset"]=  round(result.trigger_offset, round_order)    

        view_list.append(view_ind)

    return view_list

def _empty_indicator() :
    view_list = []
    view_ind = {}

    view_ind["idx"]= 0
    view_ind["type"]= "Empty"
    view_ind["interval"]= "Empty"
    view_ind["enable"]= False
    view_ind["weight_config"]= 0
    view_ind["comparator"]= "Empty"
    view_ind["value1"]= 0
    view_ind["value2"]= 0
    view_ind["value3"]= 0
    view_ind["value4"]= 0

    view_ind["enable_trade"]= True
    view_ind["val_to_comare"]= 0
    view_ind["weight_result"]= 0
    view_ind["delta"]= 0
    view_ind["factor"]= 0
    view_ind["factor_limit"]= 0
    view_ind["dis_text"]= "Empty"
    view_ind["trigger"]= 0
    view_ind["trigger_offset"]=  0 

    view_list.append(view_ind)
    return view_list
