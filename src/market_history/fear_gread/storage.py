from src.constants import FILE_PATH_FEAR_GREAD_HIST
import os
import csv

def load_csv() -> list[list]:
    """    
    Args:
        path(str):
            File path.
    Returns:
        list[list]:
            List of arrays. 
    """
    path = FILE_PATH_FEAR_GREAD_HIST
    if not os.path.exists(path):
        return None    
    with open(path,"r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",")
        return list(reader)

def save_csv(rows):
    """    
    Args:
        path(str):
            File path.
        rows(list[list]):
            Rows to be saved to .csv
    """
    path = FILE_PATH_FEAR_GREAD_HIST
    #Write to .csv overwrite everithing 
    with open(path,mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",")   
        writer.writerows(rows)


