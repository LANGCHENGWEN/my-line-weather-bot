# weather_today/today_weather_aggregator.py
import logging
from typing import Any, List, Dict, Optional

from config import CWA_API_KEY

from .cwa_today_api import get_cwa_today_data
from .weather_today_parser import parse_today_weather

from .cwa_3days_api import get_cwa_3days_data
from .weather_3days_parser import parse_3days_weather

from .today_uvindex_api import get_today_uvindex_data
from .today_uvindex_parser import parse_uv_index
# 導入你提供的紫外線測站映射模組
from .uv_station_mapping import get_uv_station_id

logger = logging.getLogger(__name__)

def get_today_all_weather_data(city_name: str) -> Optional[Dict]:
    """
    獲取指定城市的所有今日天氣數據，包括：
    - 36 小時天氣預報 (F-C0032-001)
    - 逐時天氣預報 (F-D0047-089)
    - 每日紫外線指數 (O-A0005-001)

    Args:
        city_name (str): 查詢的城市名稱。

    Returns:
        Optional[Dict]: 包含所有天氣數據的字典，如果獲取或解析失敗則返回 None。
    """
    # 初始化一個空的字典來存放所有數據
    all_weather_data = {
        "locationName": city_name,
        "general_forecast": None,
        "hourly_forecast": [],
        "uv_data": None
    }

    # 1. 取得 36 小時天氣預報 (F-C0032-001)
    try:
        raw_forecast_data = get_cwa_today_data(CWA_API_KEY, city_name)
        if not raw_forecast_data:
            logger.error(f"無法取得 {city_name} 的 36 小時天氣預報。")
            return None
        
        parsed_forecast = parse_today_weather(raw_forecast_data, city_name)
        if not parsed_forecast:
            logger.error(f"無法解析 {city_name} 的 36 小時天氣預報。")
            return None
        
        # 儲存解析後的數據
        all_weather_data["general_forecast"] = parsed_forecast

    except Exception as e:
        logger.error(f"處理 36 小時天氣預報時發生意外錯誤: {e}", exc_info=True)
        return None

    # 2. 取得逐時天氣預報 (F-D0047-089)
    # 這裡假設你的 hourly API 模組已經準備好
    try:
        raw_hourly_data = get_cwa_3days_data(CWA_API_KEY, city_name)
        if raw_hourly_data:
            parsed_hourly = parse_3days_weather(raw_hourly_data, city_name)
            all_weather_data["hourly_forecast"] = parsed_hourly
        else:
            logger.warning(f"未能取得 {city_name} 的逐時天氣預報，將使用預設值。")
    except Exception as e:
        logger.warning(f"處理逐時天氣預報時發生錯誤，但仍將繼續: {e}")
        all_weather_data["hourly_forecast"] = []

    # 3. 取得每日紫外線指數 (O-A0005-001)
    try:
        station_id = get_uv_station_id(city_name)
        raw_uv_data = get_today_uvindex_data(CWA_API_KEY)

        parsed_uv_data = parse_uv_index(raw_uv_data, station_id)
        all_weather_data["uv_data"] = parsed_uv_data
    except Exception as e:
        logger.warning(f"處理紫外線指數時發生錯誤，但仍將繼續: {e}")
        all_weather_data["uv_data"] = None
        
    return all_weather_data