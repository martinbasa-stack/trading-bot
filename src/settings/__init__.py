from .general import SettingsManager
from .strategies import StrategyManager
from .models import StrategyConfig, AssetManagerConfig, IndicatorConfig
from src.constants import(
    LOG_PATH_SETTINGS,
    FILE_PATH_BASIC,
    FILE_PATH_STRATEGY,
    INDICATOR_INTERVAL_LIST
)

strategies_obj = StrategyManager(file_path=FILE_PATH_STRATEGY, 
                             log_path=LOG_PATH_SETTINGS,
                             interval_list=INDICATOR_INTERVAL_LIST
                             )

settings_obj = SettingsManager(file_path=FILE_PATH_BASIC, 
                           log_path=LOG_PATH_SETTINGS)