from src.settings.main import strategies_obj
from src.binance.stream.thread import binance_stream_man_obj
from src.pyth.main import pyth_data_obj
from src.assets.analyzer import AssetAnalyzer
from src.assets.main import assets_man_binance_obj, assets_man_solana_obj
from src.market_history.market import market_binance_hist_obj, fear_gread_obj, market_pyth_hist_obj
from src.market_history.price.manager import MarketHistoryManager

from .trades import TradeAnalyzer
from .trades.main import trade_manager_obj
from .indicators import IndicatorCompute
from .record_HL.manager import HLRecordManager
from .dca import DCAstrategy


def build_objects(type_s, record_obj : HLRecordManager) -> tuple[TradeAnalyzer, IndicatorCompute, AssetAnalyzer, DCAstrategy, MarketHistoryManager , callable]:
    # Select object depending on strategy type
    hist_obj = market_binance_hist_obj
    stream_get_close = binance_stream_man_obj.get_close
    assets_man_obj = assets_man_binance_obj

    if market_pyth_hist_obj.provider in type_s:
        hist_obj = market_pyth_hist_obj
        stream_get_close = pyth_data_obj.get_close
        assets_man_obj = assets_man_solana_obj

    trade_analyzer_obj = TradeAnalyzer(get_trade_table=trade_manager_obj.get_table,
                                get_hist_table=hist_obj.get_table,
                                get_by_id=strategies_obj.get_by_id
                                )
    indicators_obj =IndicatorCompute(
        strategies_obj=strategies_obj,
        get_all_avg=trade_analyzer_obj.get_all_avgs,
        get_hist_table=hist_obj.get_table,
        get_close=stream_get_close,
        fear_gread_get=fear_gread_obj.get
        )
    asset_analyzer_obj = AssetAnalyzer(
        get_by_id=strategies_obj.get_by_id,
        get_all_avg=trade_analyzer_obj.get_all_avgs,
        get_available_balance=assets_man_obj.get_available,
        get_close=stream_get_close
    )

    dac_strategy = DCAstrategy(
        strategies_obj=strategies_obj,
        trade_analyzer_obj = trade_analyzer_obj,
        indicators_obj = indicators_obj,
        asset_analyzer_obj = asset_analyzer_obj,
        stream_get_close = stream_get_close,
        record_obj = record_obj 
    )
    return trade_analyzer_obj, indicators_obj, asset_analyzer_obj, dac_strategy, hist_obj, stream_get_close
