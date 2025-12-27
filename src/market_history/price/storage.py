from src.constants import BASE_DIR
import os
import numpy as np
import csv
from pathlib import Path

def load_csv(path:str) -> list[list]:
    """    
    Args:
        path(str):
            File path.
    Returns:
        list[list]:
            List of Numpy arrays ready for TA. 
    """
    if not os.path.exists(path):
        return None
    arr = np.genfromtxt(path, delimiter=",")
    return arr

def save_csv(path:str, rows:list[list]):
    """    
    Args:
        path(str):
            File path.
        rows(list[list]):
            Rows to be saved to .csv
    """
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")  
        writer.writerows(rows)

def delete_csv(paths_to_keep: list[Path], provider:str):
    """
    Delete all files with "_candle_" in the name that are NOT in provided list.
    Args:
        paths_to_keep(list[Path]):
            List of file paths to keep.
        provider(str):
            Only delete files that the same class made.
    """
    data_dir = BASE_DIR / "data"

    # Normalize keep list (absolute resolved Paths)
    keep_set = {p.resolve() for p in paths_to_keep}

    for file in data_dir.iterdir():
        if file.is_file() and f"{provider}_candle_" in file.name:
            if file.resolve() not in keep_set:
                print(f"DELETE: {file}")
                file.unlink()

def build_candle_path(symbol1 :str, symbol2:str, interval:str, provider: str):
    """
    Builds a path for a history file.
    
    Args:

        symbol1(str):
            First Symbol.
        symbol2(str):
            Second Symbol.
        interval(str):
            Candle interval as "1d", "1w", etc.
    """
    return (
        BASE_DIR
        / "data"
        / f"_{symbol1}_{symbol2}_{provider}_candle_{interval}.csv"
    )

