from .response_utils import status_msg, strategy_status, active_strategy_list, last_trade, num_trades, get_local_ip, strategy_ids

# Recive telegram message in text
def on_message_response(text:str) -> str:

    if text == "status":
        return status_msg()

    elif "id-list" == text:            
        return strategy_ids()
    
    elif "strategy:" in text:            
        val = text[text.find(":")+1 :]
        return strategy_status(val.strip())

    elif "strategy-list" == text:            
        return active_strategy_list()
                    
    elif "last-trade:" in text:   
        val = text[text.find(":")+1 :]     
        return last_trade(val.strip())
    
    elif "-trades:" in text:
        num = text[ : text.find("-")]
        val = text[text.find(":")+1 :]     
        return num_trades(num.strip(),val.strip())
        
    elif "get-ip" in text:       
        return get_local_ip()

    elif "run:" in text:   
        val = text[text.find(":")+1 :]     
        return f"Wanted to RUN ID: {val.strip()} Not supported."  
        
    elif "stop:" in text:   
        val = text[text.find(":")+1 :]
        return f"Wanted to STOP ID: {val.strip()} Not supported."  

    elif "cmds" == text:   
        return "status \nstrategy: 'ID' \nstrategy-list \nlast-trade: 'ID' \n'num' -trades: 'ID'\nget-ip\nid-list\ncmds"
    
    return None