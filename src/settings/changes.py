from .models import StrategyConfig

def get_changes(new:list[dict], old:list[dict]) -> str:
    """
    Compares changes made to strategy settings
    Args:
        new(list[dict]):
            Updated list of strategies
        old(list[dict]):
            Old list of strategies.
    Returns:
        str:
         Returns formated string of changes for logger.
    """

    if len(old) > len(new): #Strategy was deleted
        #search for deleted
        newList = []
        for setting in new:#Buld a list of new IDs
            if not setting["id"] in newList:
                newList.append(setting["id"])
        for setting in old:#check for missing ID
            if not setting["id"] in newList:
                deleted = setting #if id is not in the list it was deleted                    
                break
        #write the log
        changes=_add_delete(deleted)     
        return f"Strategy deleted: {changes}"
        
    if len(old) < len(new): #Strategy was added at the end
        added = new[-1] #Last strategy was added
        changes=_add_delete(added)            
        return f"Strategy added: {changes}"
    
    if len(old) == len(new): # check what was changed 
        changes=""
        changed_idx = None
        for index, strategy in enumerate(new): #go trough list
            for key, item in strategy.items():
                if "Dynamic" in key: #call function to search changes in indicators
                    inddicator_change = ""
                    inddicator_change = _indicator_changes(old[index][key], item)
                    if len(inddicator_change) >1: #if function returned any string save the index
                        changed_idx = index
                        changes += f"\n | changes to indicators {key}: {inddicator_change}" 
                else: #else compare key values 
                    if old[index][key] != item:
                        changed_idx = index # write the index of a list where change was made
                        changes += f"\n | {key} OLD = {old[index][key]} / NEW = {item} | " #Add change with \n -> new line
            
        if changed_idx != None:
            return f"Strategy settings changes for id{new[changed_idx]["id"]}: {changes}"                 
        return None

def _add_delete(strategy):
    changes = ""
    for key in strategy:
        if "Dynamic" in key: 
            changes += f"\n| {key} indicators: "
            for index, indDic in enumerate(strategy[key]):
                changes += f"\n Indicator id={index}:"
                for setKey in indDic:
                    changes += f" {setKey} = {indDic[setKey]} |"
        else:
            changes += f"\n| {key} = {strategy[key]} |"
    return changes

def _indicator_changes(old, new):
    changes = ""
    if len(new) > len(old): #new indicators were added
        long = list(new)
        short = list(old)
        long_str = "NEW"
        short_str = "OLD"
    else:
        long = list(old)
        short = list(new)
        long_str = "OLD"
        short_str = "NEW"
    shortMax = len(short) -1 #Max index for short
    for index, long_dict in enumerate(long):#run trough the longest
        if index > shortMax: #if index is bigger than the lenght of short than new indicators were adde
            changes += f"\n | {long_str} indicator: {long_dict} |" #add values of the indicator to the line old if deleted or new if added
        else: #Check for changes
            changed_index = None
            value_changes = ""
            for key in long_dict:
                if short[index][key] != long_dict[key]:
                    changed_index = index
                    value_changes += f" for {key} {short_str} = {short[index][key]} / {long_str} = {long_dict[key]} |" #build text of values that were changed
            if changed_index != None:
                changes += f"\n | changes for indicator id={changed_index} : {value_changes}" #If indicator was changed add to changes
    return changes