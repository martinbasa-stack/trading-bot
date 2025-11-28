import os
import csv
def load_csv(path):
    if not os.path.exists(path):
        return None    
    with open(path,"r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",")
        return list(reader)

def save_csv(path, rows):
    #Write to .csv overwrite everithing 
    with open(path,mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",")   
        writer.writerows(rows)

def delete_csv(paths_to_delete):
    for path in paths_to_delete:
        if os.path.exists(path):
            os.remove(path)

def build_trade_path(symbol1, symbol2, id, type_s, paper=""):
    path = f"data/_{paper}Trade_{type_s}_{symbol1}_{symbol2}_{id}_.csv"
    return path

