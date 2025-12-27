from src.constants import(
    FILE_PATH_HIST_STRATEGY
)
from src.settings.main import strategies_obj

from .manager import HLRecordManager


#Create long lived objects
record_obj =  HLRecordManager(path=FILE_PATH_HIST_STRATEGY, get_list_of_id_pair=strategies_obj.get_id_pair_list)