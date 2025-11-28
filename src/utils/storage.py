import os
import json

def load_json(path):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r") as jf: #open file
            return json.load(jf)  #return json
    except Exception as e:
        print(f"load_json() error: {e}")

def save_json(path,data): 
    try:   
        with open(path, "w") as jf: # save list of assets as JSON
            json.dump(data, jf, ensure_ascii=False, indent=4)   
    except Exception as e:
        print(f"save_json() error: {e}")


