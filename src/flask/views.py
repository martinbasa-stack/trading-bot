from src.settings import settings_class, strategies_class
from src.history import history_class, PairHistory, IntervalData
from src.trades import trade_manager_class, Trade, TradeTable
from datetime import datetime, timezone



def trade_table_view():
    view = {} #Cleare the whole table before creating
    
    for id_ in strategies_class.id_list():
        trade_table = trade_manager_class.get_table(id_)    
        if trade_table is None:
            continue
        strategy = strategies_class.get_by_id(id_)
        if strategy is None:
            continue 
        table_view = []
        reversed_arr  = trade_table[::-1]#Reorder from new to old new at the top
        for i in reversed_arr:   # Formating of timestamp and converting all to string since it is only for display
            tempTupple = (
            str(datetime.fromtimestamp(int(i.timestamp/1000))), 
            str(i.idx),
            str(i.symbol1),
            str(i.quantity1),
            str(i.symbol2),
            str(i.quantity2),
            str(i.price),
            str(round(i.change,2)),
            str(i.commision),
            str(i.commision_symbol)
            )       
            table_view.append(tempTupple)  

        if not table_view: #If empty write a defaule empty tuple for template rendering
            table_view = [(0,"Empty","Symbol1",0,"Symbol2",0,0,0,0,"SymbolC")] 
        view[id_] = {} # initiate / if exist it will cleare the strategy trade data
        #Fill base data
        s1 = strategy["Symbol1"]
        s2 = strategy["Symbol2"]
        view[id_]["Symbol1"] = s1
        view[id_]["Symbol2"] = s2
        view[id_]["CandleInterval"] = strategy["CandleInterval"]
        view[id_]["type"] = strategy["type"]
        view[id_]["paperTrading"] = strategy["paperTrading"]
        view[id_]["name"] = f"{strategy["name"]}_{s1}_{s2}"
        view[id_]["trades"] = table_view
    
    return view