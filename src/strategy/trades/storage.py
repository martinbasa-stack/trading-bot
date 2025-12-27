from src.constants import BASE_DIR
import os
import csv

def load_csv(path) -> list[list]:
    """    
    Args:
        path(str):
            File path.
    Returns:
        list[list]:
            List of arrays. 
    """
    if not os.path.exists(path):
        return None    
    with open(path,"r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",")
        return list(reader)

def save_csv(path, rows):
    """    
    Args:
        path(str):
            File path.
        rows(list[list]):
            Rows to be saved to .csv
    """
    #Write to .csv overwrite everithing 
    with open(path,mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",")   
        writer.writerows(rows)

def delete_csv(paths_to_delete: list[str]):
    """    
    Delet all files in the paths_to_delete.
    Args:
        paths_to_delete(list[str]):
            List of file paths to delete.
    """
    for path in paths_to_delete:
        if os.path.exists(path):
            os.remove(path)            
            print(f"DELETE: {path}")

def build_trade_path(symbol1, symbol2, idx, type_s, paper=""):
    """
    Builds a path for a trade file.

    Args:

        symbol1(str):
            First Symbol.
        symbol2(str):
            Second Symbol.
        idx(Any):
            Strategy ID.
        paper(str):
            String to attach at start of file name.

    """
    path = (
        BASE_DIR
        / "data"
        / f"_{paper}Trade_{type_s}_{symbol1}_{symbol2}_{idx}_.csv"
    )
    return path

