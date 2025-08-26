# weather_today/weather_3days_parser.py
"""
解析中央氣象署「未來 3 天天氣預報」API (F-D0047-089) 的原始數據。
主要職責：
1. 定位數據：從複雜的 JSON 結構中，根據地點名稱精確的找到目標地點的數據。
2. 提取關鍵資訊：從每個小時的時間條目中，提取出天氣元素，例如體感溫度、相對濕度、風速和風向。
3. 數據格式化與處理：對提取出的數值進行格式化，例如將體感溫度加上「°C」，將風速轉換為蒲福風級，並加上文字描述，同時保留原始數值以供後續的邏輯判斷使用。
4. 錯誤處理與回退：處理數據缺失、格式無效或解析失敗等各種情況，確保在發生錯誤時，程式能安全的返回 None，避免崩潰。
"""
import logging
from utils.weather_utils import get_beaufort_scale_description, convert_ms_to_beaufort_scale

logger = logging.getLogger(__name__)

# --- 解析從中央氣象署 API 獲取到的原始 JSON 數據 ---
def parse_3days_weather(data: dict, location_name: str) -> list | None:
    """
    提取指定地點的未來 3 天天氣元素（體感溫度、相對濕度、風速、風向）。
    驗證傳入數據的有效性，然後遍歷 JSON 結構以找到目標城市。
    找到目標城市後，再次遍歷數據中的天氣元素，並根據時間點將不同類型的數據聚合到同一個字典中。
    將風速等數值轉換為更具可讀性的格式，並在整個過程中處理可能出現的錯誤。

    Args:
        data (dict): 從中央氣象署 API 獲取到的原始 JSON 資料。
        location_name (str): 縣市名稱。

    Returns:
        list: 包含未來 3 天天氣數據的列表，如果數據不存在或地點未找到則返回 None。
    """
    parsed_data = []

    # 檢查數據是否為空，以及是否包含 `'records'` 鍵
    if not data or "records" not in data:
        logger.warning("傳入的天氣數據無效或缺少 'records' 鍵。")
        return None # 返回 None 表示解析失敗
    
    # 從 records 中獲取 Locations 列表
    locations_entries = data["records"].get("Locations", [])
    if not locations_entries:
        logger.warning("天氣數據中 'records' 下的 'Locations' 列表為空或不存在。")
        return None

    # --- 在多層嵌套的 JSON 結構中，找到與 `location_name` 相匹配的數據 ---
    """
    使用兩個嵌套的迴圈：外層迴圈遍歷 `Locations`，內層迴圈遍歷每個 `Locations` 下的 `Location`。
    一旦找到匹配的 `'LocationName'`，就會將該數據賦值給 `target_location_data` 並立即跳出迴圈。
    """
    target_location_data = None
    # 遍歷 `Locations` 列表，找到包含目標地點的數據
    for loc_entry in locations_entries:
        sub_locations = loc_entry.get("Location", []) # 獲取內層的 Location 列表
        # 遍歷 `Location` 列表
        for sub_loc in sub_locations:
            if sub_loc.get("LocationName") == location_name:
                target_location_data = sub_loc
                break
        if target_location_data: # 找到目標地點後就停止遍歷
            break

    if not target_location_data:
        logger.warning(f"在原始天氣數據中未找到 '{location_name}' 的詳細位置數據。")
        return None
    
    weather_elements_map = {}

    weather_elements = target_location_data.get("WeatherElement", []) # 提取天氣元素
    if not weather_elements:
        logger.warning(f"'{location_name}' 的天氣數據中未找到 'WeatherElement'。")
        return None
    
    relevant_elements = ["體感溫度", "相對濕度", "風速", "風向"] # 只處理想要的天氣元素

    # --- 遍歷目標地點下的所有 `'WeatherElement'` ---
    for element in weather_elements:
        element_name = element.get("ElementName")
        if element_name in relevant_elements:
            for time_entry in element.get("Time", []):
                data_time = time_entry.get("DataTime")                  # 提取每個時間點
                element_value_list = time_entry.get("ElementValue", []) # 提取數據列表

                if not data_time or not element_value_list:
                    continue # 跳過無效的時間或數據列表

                element_value = element_value_list[0] # 取第一個項目，且確保列表不為空

                # 檢查某個時間點是否已經在 `weather_elements_map` 字典裡
                if data_time not in weather_elements_map:
                    weather_elements_map[data_time] = {"DataTime": data_time}

                # 使用一個字典 `weather_elements_map` 按時間點聚合不同類型的天氣數據
                if element_name == "體感溫度":
                    try:
                        at_value = element_value.get("ApparentTemperature")
                        at_float = float(at_value)
                        weather_elements_map[data_time]["apparent_temp_formatted"] = f"{round(at_float, 1)}°C"
                        weather_elements_map[data_time]["apparent_temp_raw"] = at_float # 保留原始數值供穿搭判斷
                    except (ValueError, TypeError):
                        weather_elements_map[data_time]["apparent_temp_formatted"] = "無資料"
                        weather_elements_map[data_time]["apparent_temp_raw"] = None
                elif element_name == "相對濕度":
                    try:
                        rh_value = element_value.get("RelativeHumidity")
                        rh_float = float(rh_value)
                        weather_elements_map[data_time]["humidity_formatted"] = f"{round(rh_float)}%"
                        weather_elements_map[data_time]["humidity_raw"] = rh_float # 保留原始數值供穿搭判斷
                    except (ValueError, TypeError):
                        weather_elements_map[data_time]["humidity_formatted"] = "無資料"
                        weather_elements_map[data_time]["humidity_raw"] = None
                elif element_name == "風速":
                    try:
                        ws_value = element_value.get("WindSpeed")
                        ws_float = float(ws_value)
                        
                        # 將原始數值轉換為更友善的蒲福風級和描述
                        wind_scale_int = convert_ms_to_beaufort_scale(ws_float)
                        wind_scale_desc = get_beaufort_scale_description(wind_scale_int)
                        weather_elements_map[data_time]["wind_scale_formatted"] = f"{wind_scale_int} 級 ({wind_scale_desc})"
                        weather_elements_map[data_time]["wind_scale_raw"] = wind_scale_int # 保留純數字蒲福風級供穿搭判斷
                    except (ValueError, TypeError):
                        weather_elements_map[data_time]["wind_scale_formatted"] = "無資料"
                        weather_elements_map[data_time]["wind_scale_raw"] = None
                elif element_name == "風向":
                    weather_elements_map[data_time]["wind_direction"] = element_value.get("WindDirection", "無資料")

    if not weather_elements_map:
        logger.warning(f"未能從 '{location_name}' 的天氣數據中解析出任何有效的天氣元素。")
        return None

    # 將以時間為鍵的字典轉換回一個列表，並確保時間順序是正確的
    parsed_data = sorted(weather_elements_map.values(), key=lambda x: x["DataTime"])
    return parsed_data # 返回列表