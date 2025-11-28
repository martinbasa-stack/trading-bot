import os
import numpy as np
import csv

def load_csv(path):
    if not os.path.exists(path):
        return None
    arr = np.genfromtxt(path, delimiter=",")
    return arr

def save_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")  
        writer.writerows(rows)

def delete_csv(paths_to_keep):
    entries = os.listdir("data") # get all file names in directory
    for entry in entries:
        if "_candle_" in entry and not f"data/{entry}" in paths_to_keep: #delet all that are not needed
            os.remove(f"data/{entry}") #remove file

def build_candle_path(symbol1, symbol2, interval):
    return f"data/_{symbol1}_{symbol2}_candle_{interval}.csv"

