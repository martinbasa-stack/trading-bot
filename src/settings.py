from .constants import (
    FILE_PATH_STRATEGY,
    FILE_PATH_BASIC,
    LOG_PATH_SETTINGS
)

import json
import logging



# Create a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent propagation to the root logger
logger.propagate = False
# Create a file handler for this module's log file
file_handler = logging.FileHandler(LOG_PATH_SETTINGS, mode="a")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def loadBsettings():
    try:
        with open(FILE_PATH_BASIC, "r") as jf: # open list of settings as JSON
            data = json.load(jf)     
            #logger.info(f"Loaded basic settings")# {data}")
            return data
    except Exception as e:
        logger.error(f"Loading basic settings error: {e}")

def saveBsettings(data):
    try:
        old = loadBsettings()
        with open(FILE_PATH_BASIC, "w") as jf: # open list of settings as JSON
            json.dump(data,jf, ensure_ascii=False, indent=4)     
        change = ""
        for key in data: #Search for changes made
            if old[key] != data[key]: 
                if "API_" in key or "telegram_TOKEN" in key or "password" in key: #Do not log changes in API_ or telegram_TOKEN
                    change += f"\n| {key} was changed | "
                else:
                    change += f"\n| {key} OLD = {old[key]} / NEW = {data[key]} | "
        if len(change) > 2:
            logger.info(f"Basic settings changes : {change}")
        return data
    except Exception as e:
        logger.error(f"Save basic settings error: {e}")
#---------------------------------------------------------------------------------------------

def loadStrSettings():
    try:
        with open(FILE_PATH_STRATEGY, "r") as jf: # open list of settings as JSON
            data = json.load(jf)                    
            #logger.info(f"Loaded strategy settings")# {data}")
            return data
    except Exception as e:
        logger.error(f"Loading strategy settings error: {e}")

def saveStrSettings(data):
    try:
        old = loadStrSettings()
        with open(FILE_PATH_STRATEGY, "w") as jf: # open list of settings as JSON
            json.dump(data,jf, ensure_ascii=False, indent=4)  
        if len(old) > len(data): #Strategy was deleted
            #search for deleted
            newList = []
            for setting in data:#Buld a list of new IDs
                if not setting["id"] in newList:
                    newList.append(setting["id"])

            for setting in old:#check for missing ID
                if not setting["id"] in newList:
                    deleted = setting #if id is not in the list it was deleted                    
                    break
            #write the log
            formatedStr=""
            for key in deleted:
                if "Dynamic" in key: 
                    formatedStr += f"\n| {key} indicators: "
                    for index, indDic in enumerate(deleted[key]):
                        formatedStr += f"\n Indicator id={index}:"
                        for setKey in indDic:
                            formatedStr += f" {setKey} = {indDic[setKey]} |"
                else:
                    formatedStr += f"\n| {key} = {deleted[key]} |"
            logger.info(f"Strategy deleted: {formatedStr}")
            
        if len(old) < len(data): #Strategy was added at the end
            new = data[-1] #Last strategy was added
            formatedStr=""
            for key in new:
                if "Dynamic" in key: 
                    formatedStr += f"\n| {key} indicators: "
                    for index, indDic in enumerate(new[key]):
                        formatedStr += f"\n Indicator id={index}:"
                        for setKey in indDic:
                            formatedStr += f" {setKey} = {indDic[setKey]} |"
                else:
                    formatedStr += f"\n| {key} = {new[key]} |"
            logger.info(f"Strategy added: {formatedStr}")
        
        if len(old) == len(data): # check what was changed 
            changes=""
            changedIndex = None
            for index, new in enumerate(data): #go trough list
                for key in new.keys():
                    if "Dynamic" in key: #call function to search changes in indicators
                        indChange = ""
                        indChange = _indicatorChanges(old[index][key], new[key])
                        if len(indChange) >3: #if function returned any string save the index
                            changedIndex = index
                            changes += f"\n | changes to indicators {key}: {indChange}" 
                    else: #else compare key values 
                        if old[index][key] != new[key]:
                            changedIndex = index # write the index of a list where change was made
                            changes += f"\n | {key} OLD = {old[index][key]} / NEW = {new[key]} | " #Add change with \n -> new line
             
            if changedIndex != None:
                logger.info(f"Strategy settings changes for id{data[changedIndex]["id"]}: {changes}")
        return data
    except Exception as e:
        logger.error(f"save strategy settings error: {e}")

def _indicatorChanges(old, new):
    try:
        changes = ""
        if len(new) > len(old): #new indicators were added
            long = list(new)
            short = list(old)
            longStr = "NEW"
            shortStr = "OLD"
        else:
            long = list(old)
            short = list(new)
            longStr = "OLD"
            shortStr = "NEW"
        shortMax = len(short) -1 #Max index for short
        for index, longDic in enumerate(long):#run trough the longest
            if index > shortMax: #if index is bigger than the lenght of short than new indicators were adde
                changes += f"\n | {longStr} indicator: {longDic} |" #add values of the indicator to the line old if deleted or new if added
            else: #Check for changes
                changedIndex = None
                valueChanges = ""
                for key in longDic:
                    if short[index][key] != longDic[key]:
                        changedIndex = index
                        valueChanges += f" for {key} {shortStr} = {short[index][key]} / {longStr} = {longDic[key]} |" #build text of values that were changed
                if changedIndex != None:
                    changes += f"\n | changes for indicator id={changedIndex} : {valueChanges}" #If indicator was changed add to changes
        return f"{changes}"
    except Exception as e:
        logger.error(f"indicatorChanges() error: {e}")
    
if __name__ == "__main__":  
#Populate variables    
    loadBsettings()
    loadStrSettings()