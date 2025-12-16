import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.market_history import fear_gread_obj

fear_gread_obj._update()

print(f"TEST fear_gread_obj.get {fear_gread_obj.get()}")
print(f"TEST fear_gread_obj.get_timestamp = {fear_gread_obj.get_timestamp(1764609377)}")

#print(f"TEST fear_gread_obj.get_hist {fear_gread_obj.get_hist()}")
