from .models import Assets, Balance, AssetManagerResult
from .analyzer import AssetAnalyzer
from .manager import AssetManager
from src.settings import strategies_obj

asset_manager_obj = AssetManager(get_by_id=strategies_obj.get_by_id)