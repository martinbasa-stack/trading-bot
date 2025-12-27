from src.settings.main import strategies_obj
from src.strategy.record_HL.main import record_obj
from src.strategy.utils import build_objects
from src.models import Trade
from src.strategy.trades.main import trade_manager_obj
from src.binance.websocket.thread import  ws_manager_obj
from src.binance.stream.thread import binance_stream_man_obj
from src.pyth.main import pyth_data_obj
from src.wallet.main import vault_obj

import socket
from datetime import datetime, timezone, timedelta


def _now():        
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp()) 
    
app_start = _now()

def _custom_round(val:float, min_dec: int = 2):
    """
    Return rounded value with auto adjustable decimal places in order to not display 0
    Args:
        val(float):
            Value you want to round

        min_dec(int, optional):
            Minimum decimal places to round.
    
    Returns:
        float: 
            Rounded number.
    """
    temp = abs(val)
    count_round = min_dec
    while temp < 1 and temp > 0:
        temp = temp*10
        count_round +=1  
    return round(val, count_round)


def get_local_ip():
    """Tries to determine the local IP address by connecting to a reliable external server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except socket.error:
        ip = '127.0.0.1' # Fallback to loopback if no network connectivity
    finally:
        s.close()
    return ip

def last_trade(idx:str) -> str:
    msg = f"'{idx}' is not a strategy ID \n {active_strategy_list()}"
    if not idx:
        return msg
    if not idx.isnumeric():
        return msg
    
    idx = int(idx)
    s = strategies_obj.get_by_id(idx)
    if not s:
        return msg
    
    trade = trade_manager_obj.get_last_trade(idx)
    if not trade:
        return f"No trades for strategy ID : {idx}\n"
    
    msg = (f"Last trade for:\n"
            f"Strategy ID: {s.idx} pair: {s.symbol1}/{s.symbol2}\n"
            f" Type: {s.type_s}\n"
            f" Name: {s.name} \n")
    msg += _msg_from_trade(idx, trade)
    return msg

def num_trades(num: str, idx:str) -> str:    
    msg = f"'{num}' has to be a number!"
    if not num:
        return msg
    if not num.isnumeric():
        return msg
    
    msg = f"'{idx}' is not a strategy ID \n {active_strategy_list}"
    if not idx:
        return msg
    if not idx.isnumeric():
        return msg
    
    num = int(num)
    num = min(num, 10)

    idx = int(idx)
    s = strategies_obj.get_by_id(idx)
    if not s:
        return msg
    
    trades = trade_manager_obj.get_table(idx)

    if not trades:
        return f"No trades for strategy ID : {idx}\n"
    
    msg = (f"List of last {num} trades for:\n"
            f"Strategy ID: {s.idx} pair: {s.symbol1}/{s.symbol2} \n"
            f" Type: {s.type_s}\n"
            f" Name: {s.name} \n")
    msg += "-------------------------------\n"
    rev_trades = trades[::-1]
    for index, trade in enumerate(rev_trades):
        if index >= num:
            break
        msg +=_msg_from_trade(idx, trade)
        msg += "-------------------------------\n"
    
    return msg

def _msg_from_trade(idx, trade: Trade):    
    side = "SELL"
    if trade.quantity1 > 0:
        side =  "BUY"
    return (
        f"  Timestamp: {datetime.fromtimestamp(int(trade.timestamp/1000))} \n"
        f"  ID: {trade.idx} \n"
        f"  Side: {side} \n"
        f"  Ammount:\n"
        f"     {_custom_round(trade.quantity1)} {trade.symbol1} | {_custom_round(trade.quantity2)} {trade.symbol2} \n"
        f"  Price: {_custom_round(trade.price)} {trade.symbol2}\n"
        f"  Commision: {_custom_round(trade.commision)} {trade.commision_symbol}\n"
        f"  Change: {round(trade.change, 2)} %\n"
    )

def strategy_status(idx:str) -> str:
    msg = f"{idx} is not a strategy ID. \n {active_strategy_list()}"
    if not idx:
        return msg
    if not idx.isnumeric():
        return msg
    
    idx = int(idx)
    s = strategies_obj.get_by_id(idx)
    if not s.run:
        return f"Strategy {idx} is not running. \n {active_strategy_list()}"
    
    trade_analyzer_obj, _, asset_analyzer_obj, dac_strategy, _, get_close = build_objects(s.type_s, record_obj)
    last_close = get_close(f"{s.symbol1}{s.symbol2}")
    pnl = trade_analyzer_obj.get_pnl(idx, last_close)
    entry, cost, exit_ = trade_analyzer_obj.get_all_avgs(idx)
    compute_dca = dac_strategy.get_trigger_compute(idx)
    paper_live = "LIVE"
    if s.asset_manager.paper_t:
        paper_live = "paper"

    avail_s1 = asset_analyzer_obj.get_available(s.symbol1)
    avail_s2 = asset_analyzer_obj.get_available(s.symbol2)
    
    msg = (
        f"Strategy ID: {s.idx} pair: {s.symbol1}/{s.symbol2} \n"
        f" Type: {s.type_s}\n"
        f" Name: {s.name} \n"
        f"Price: {_custom_round(last_close)} {s.symbol2} \n"
        f"-------------------------------\n"
        f"Profit/Loss: \n"
        f"  Total: {_custom_round(pnl.total)} {s.symbol2} | {round(pnl.total_percent,2)} %\n"
        f"  Realised: {_custom_round(pnl.realised)} {s.symbol2} | {round(pnl.real_percent,2)} %\n"
        f"  Unrealised: {_custom_round(pnl.unrealised)} {s.symbol2} | {round(pnl.unreal_percent,2)} %\n"
        f"Average:\n"
        f"  Entry: {_custom_round(entry.avg)} {s.symbol2} \n"
        f"  Cost: {_custom_round(cost.avg)} {s.symbol2} \n"
        f"  Exit: {_custom_round(exit_.avg)} {s.symbol2} \n"
        f"-------------------------------\n"
        f"Trade status: {paper_live}\n"
        f"  Buy:\n"
        f"    change: {round(compute_dca.percent_change_dip,2)} % / {s.asset_manager.dip_buy} %\n"
        f"    min price: {compute_dca.min_price} {s.symbol2}\n"
        f"    Indicators: {compute_dca.buy_ind_trade_en} Weight: {compute_dca.buy_weight} / {s.asset_manager.min_weight_buy} \n"
        f"    num. trades: {entry.num}\n"
        f"  Sell:\n"
        f"    change: {round(compute_dca.percent_change_pump, 2)} % / {s.asset_manager.pump_sell} %\n"
        f"    max price: {compute_dca.max_price} {s.symbol2}\n"
        f"    Indicators: {compute_dca.sell_ind_trade_en} Weight: {compute_dca.sell_weight} / {s.asset_manager.min_weight_sell} \n"
        f"    num. trades: {exit_.num}\n"
        f"-------------------------------\n"
        f"Balance: \n"
        f"  Available {_custom_round(avail_s1)} {s.symbol1} \n"
        f"  Available {_custom_round(avail_s2)} {s.symbol2} \n"
        )
    return msg

def active_strategy_list():  
    active_all, _, _ = _active_strategies()
    return f"All running strategies: {active_all}"


def strategy_ids():    
    return f"Available strategy ids:\n{strategies_obj.get_id_list()}"

def _active_strategies() -> tuple[dict, dict, dict]:    
    active_live = ""
    active_all = ""
    active_paper = ""
    for s in strategies_obj.get_all():
        if s.run:
            txt = f"\n ID: {s.idx}: pair: {s.symbol1}/{s.symbol2}\n on: {s.type_s}"
            active_all += txt
            if not s.asset_manager.paper_t:
                active_live += txt
            else:
                active_paper += txt

    return active_all, active_live, active_paper


def status_msg() -> str:
    last_ping = ws_manager_obj.get_last_ping_resp()  
    _, active_live, active_paper = _active_strategies()
      
    wallet = "Unlocked"
    if vault_obj.locked:
        wallet= "Locked"
    return (
        f"Startup at {datetime.fromtimestamp(app_start)} | running for {timedelta(seconds = _now() - app_start)} \n"        
        f"Wallets: {wallet} \n"
        f"Active LIVE strategies: {active_live} \n"
        f"Active paper strategies: {active_paper} \n"
        f"-------------------------------\n"
        f"Websocket connected: {ws_manager_obj.is_connected()} \n"
        f"  Last ping: {last_ping}\n"
        f"Binance Stream connected: {binance_stream_man_obj.is_connected()} \n"
        f"  Oldest: {binance_stream_man_obj.oldest()} s, since {datetime.fromtimestamp(binance_stream_man_obj.oldest_timestamp())} \n"
        f"  Streams: {list(binance_stream_man_obj.get_active_list().keys())} \n"
        f"-------------------------------\n"
        f"Pyth Stream connected: {pyth_data_obj.is_connected()} \n"
        f"  Oldest: {pyth_data_obj.oldest()} s, since {datetime.fromtimestamp(pyth_data_obj.oldest_timestamp())} \n"
        f"  Streams: {list(pyth_data_obj.get_active_list().keys())} \n"
        )    
