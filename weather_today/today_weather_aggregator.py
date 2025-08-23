# weather_today/today_weather_aggregator.py
"""
「今日天氣」功能的數據聚合器。
將來自中央氣象署不同 API 的多種數據源整合在一起。
主要職責：
1. 協調 API 請求：依序呼叫多個不同的 API 模組（36小時預報、未來 3 天預報、紫外線指數），獲取原始數據。
2. 處理數據解析：將獲取到的原始數據傳遞給對應的解析器，轉換為結構化、易於使用的格式。
3. 整合數據：將所有解析後的數據合併到一個單一的字典中。
4. 錯誤處理：如果任何一個數據獲取或解析環節失敗，會記錄錯誤並返回 None，確保上層呼叫者能夠安全的處理失敗情況。
""" 
import logging
from typing import Dict, Optional

from config import CWA_API_KEY

from .cwa_today_api import get_cwa_today_data
from .weather_today_parser import parse_today_weather

from .cwa_3days_api import get_cwa_3days_data
from .weather_3days_parser import parse_3days_weather

from .today_uvindex_api import get_today_uvindex_data
from .today_uvindex_parser import parse_uv_index

from .uv_station_mapping import get_uv_station_id # 導入紫外線測站映射模組

logger = logging.getLogger(__name__)

def get_today_all_weather_data(city_name: str) -> Optional[Dict]:
    """
    獲取指定城市的所有今日天氣數據：
    - 36 小時天氣預報 (F-C0032-001)
    - 未來 3 天天氣預報 (F-D0047-089)
    - 每日紫外線指數 (O-A0005-001)
    所有數據流的匯集點，依序呼叫各個 API 和解析器，將結果整合在一個字典中。

    Args:
        city_name (str): 查詢的城市名稱。

    Returns:
        Optional[Dict]: 包含所有天氣數據的字典，如果獲取或解析失敗則返回 None。
    """
    # 初始化一個空的字典存放所有數據
    # 確保無論後續步驟是否成功，回傳的字典結構都保持一致
    all_weather_data = {
        "locationName"     : city_name,
        "general_forecast" : None,
        "hourly_forecast"  : [],
        "uv_data"          : None
    }

    # 1. 取得 36 小時天氣預報 (F-C0032-001)
    try:
        """
        獲取並解析 36 小時預報數據。
        如果 `get_cwa_today_data` 或 `parse_today_weather` 失敗，程式會記錄錯誤並立即返回 `None`。
        防止在缺少最關鍵數據的情況下繼續執行，避免產生無效的結果。
        """
        raw_forecast_data = get_cwa_today_data(CWA_API_KEY, city_name)
        if not raw_forecast_data:
            logger.error(f"無法取得 {city_name} 的 36 小時天氣預報。")
            return None
        
        parsed_forecast = parse_today_weather(raw_forecast_data, city_name)
        if not parsed_forecast:
            logger.error(f"無法解析 {city_name} 的 36 小時天氣預報。")
            return None
         
        all_weather_data["general_forecast"] = parsed_forecast # 儲存解析後的數據

    except Exception as e:
        logger.error(f"處理 36 小時天氣預報時發生意外錯誤: {e}", exc_info=True)
        return None

    # 2. 取得未來 3 天天氣預報 (F-D0047-089)
    try:
        """
        獲取並解析未來 3 天天氣預報數據。
        與上一個區塊不同，這部分數據被視為「非必要」的額外資訊。
        即使 `get_cwa_3days_data` 或 `parse_3days_weather` 失敗，程式也不會中斷。
        會記錄 `warning` 日誌，並將 `hourly_forecast` 設置為空列表 `[]`，然後繼續執行。
        確保主要功能（顯示 36 小時預報）在次要數據獲取失敗時仍然可用。
        """
        raw_hourly_data = get_cwa_3days_data(CWA_API_KEY, city_name)
        if raw_hourly_data:
            parsed_hourly = parse_3days_weather(raw_hourly_data, city_name)
            all_weather_data["hourly_forecast"] = parsed_hourly # 儲存解析後的數據
        else:
            logger.warning(f"未能取得 {city_name} 的未來 3 天天氣預報，將使用預設值。")
    except Exception as e:
        logger.warning(f"處理未來 3 天天氣預報時發生錯誤，但仍將繼續: {e}")
        all_weather_data["hourly_forecast"] = []

    # 3. 取得每日紫外線指數 (O-A0005-001)
    try:
        """
        獲取並解析紫外線指數數據。
        與未來 3 天天氣預報類似，這部分數據也是次要的。
        先呼叫 `get_uv_station_id` 確定應該查詢哪個測站的數據。
        接著呼叫 `get_today_uvindex_data` 和 `parse_uv_index` 獲取並解析數據。
        如果過程中發生錯誤，會記錄警告日誌並將 `uv_data` 設為 `None`，然後繼續執行。
        確保即使紫外線數據不可用，主功能也不會受影響。
        """
        station_id = get_uv_station_id(city_name)
        raw_uv_data = get_today_uvindex_data(CWA_API_KEY)

        parsed_uv_data = parse_uv_index(raw_uv_data, station_id)
        all_weather_data["uv_data"] = parsed_uv_data # 儲存解析後的數據
    except Exception as e:
        logger.warning(f"處理紫外線指數時發生錯誤，但仍將繼續: {e}")
        all_weather_data["uv_data"] = None
        
    return all_weather_data