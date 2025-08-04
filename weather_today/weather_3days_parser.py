# weather_today/weather_3days_parser.py
import logging
from datetime import datetime
from utils.weather_utils import get_beaufort_scale_description, convert_ms_to_beaufort_scale

logger = logging.getLogger(__name__)

def parse_3days_weather(data: dict, location_name: str) -> list | None:
    """
    解析從中央氣象局 API 獲取到的原始 JSON 數據，提取指定地點的逐小時天氣元素
    （體感溫度、相對濕度、風向、風速）。

    :param data: 從中央氣象局 API 獲取到的原始 JSON 數據（字典形式）。
    :param location_name: 要解析的地點名稱。
    :return: 包含逐小時天氣數據的字典 (以 DataTime 為鍵)，如果數據不存在或地點未找到則返回 None。
    """
    parsed_data = []

    if not data or "records" not in data:
        logger.warning("傳入的天氣數據無效或缺少 'records' 鍵。")
        return None # 返回 None 表示解析失敗
    
    # 從 records 中獲取 Locations 列表
    locations_entries = data["records"].get("Locations", [])
    if not locations_entries:
        logger.warning("天氣數據中 'records' 下的 'Locations' 列表為空或不存在。")
        return None

    target_location_data = None
    # 遍歷 'Locations' 列表，找到包含目標地點數據的條目
    for loc_entry in locations_entries:
        sub_locations = loc_entry.get("Location", []) # 獲取內層的 Location 列表
        for sub_loc in sub_locations:
            if sub_loc.get("LocationName") == location_name:
                target_location_data = sub_loc
                break
        if target_location_data: # 找到目標地點後就停止遍歷
            break

    if not target_location_data:
        logger.warning(f"在原始天氣數據中未找到 '{location_name}' 的詳細位置數據。")
        return None
    
    # 如果找到了目標地點數據，繼續解析其天氣元素
    weather_elements_map = {}
    weather_elements = target_location_data.get("WeatherElement", [])

    if not weather_elements:
        logger.warning(f"'{location_name}' 的天氣數據中未找到 'WeatherElement'。")
        return None
    
    relevant_elements = ["體感溫度", "相對濕度", "風速", "風向"]

    for element in weather_elements:
        element_name = element.get("ElementName")
        # 只處理我們關心的天氣元素
        if element_name in relevant_elements:
            for time_entry in element.get("Time", []):
                data_time = time_entry.get("DataTime")
                element_value_list = time_entry.get("ElementValue", [])

                if not data_time or not element_value_list:
                    continue # 跳過無效的時間或值條目

                element_value = element_value_list[0] # 假設只有一個值，且確保列表不為空

                if data_time not in weather_elements_map:
                    weather_elements_map[data_time] = {"DataTime": data_time}

                # 根據 ElementName 填充對應的鍵
                if element_name == "體感溫度":
                    # 注意：體感溫度在實際 JSON 中對應的鍵是 "ApparentTemperature"
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
                        weather_elements_map[data_time]["wind_speed_formatted"] = f"{round(ws_float, 1)} m/s"
                        weather_elements_map[data_time]["wind_speed_raw"] = ws_float # 保留原始數值供穿搭判斷
                        
                        # 在這裡將風級轉換並直接格式化為字串
                        wind_scale_int = convert_ms_to_beaufort_scale(ws_float)
                        wind_scale_desc = get_beaufort_scale_description(wind_scale_int)
                        weather_elements_map[data_time]["wind_scale_formatted"] = f"{wind_scale_int} 級 ({wind_scale_desc})"
                        weather_elements_map[data_time]["wind_scale_raw"] = wind_scale_int # 純數字風級
                    except (ValueError, TypeError):
                        weather_elements_map[data_time]["wind_speed_formatted"] = "無資料"
                        weather_elements_map[data_time]["wind_speed_raw"] = None
                        weather_elements_map[data_time]["wind_scale_formatted"] = "無資料" # 無法解析風速時，風級也給 N/A
                        weather_elements_map[data_time]["wind_scale_raw"] = None
                elif element_name == "風向":
                    weather_elements_map[data_time]["wind_direction"] = element_value.get("WindDirection", "無資料")

    if not weather_elements_map:
        logger.warning(f"未能從 '{location_name}' 的天氣數據中解析出任何有效的天氣元素。")
        return None
            
    # 將字典轉換為列表並按時間排序
    # 通常逐小時數據會以列表形式返回，所以這裡保持列表形式
    parsed_data = sorted(weather_elements_map.values(), key=lambda x: x["DataTime"])

    return parsed_data # 返回列表

# # 範例用法 (需要先有原始 JSON 數據)
# if __name__ == "__main__":
#     # 這裡需要一個類似 weather_api_client.py 獲取到的實際 JSON 數據
#     # 為了測試，我們使用一個簡化的示例數據結構
#     sample_json_data = {
#         "success": "true",
#         "result": {
#             "resource_id": "F-D0047-089",
#             "fields": [
#                 {"id": "LocationName", "type": "String"},
#                 {"id": "ElementName", "type": "String"},
#                 {"id": "DataTime", "type": "String"},
#                 {"id": "RelativeHumidity", "type": "String"},
#                 {"id": "WindDirection", "type": "String"},
#                 {"id": "WindSpeed", "type": "String"},
#                 {"id": "ApparentTemperature", "type": "String"}
#             ]
#         },
#         "records": {
#             "Locations": [
#                 {
#                     "DatasetDescription": "臺灣各縣市鄉鎮未來3天天氣預報",
#                     "LocationsName": "台灣",
#                     "Dataid": "D0047-089",
#                     "Location": [
#                         {
#                             "LocationName": "臺中市",
#                             "Geocode": "66000000",
#                             "Latitude": "24.142918",
#                             "Longitude": "120.66295",
#                             "WeatherElement": [
#                                 {
#                                     "ElementName": "相對濕度",
#                                     "Time": [
#                                         {"DataTime": "2025-07-24T12:00:00+08:00", "ElementValue": [{"RelativeHumidity": "74"}]},
#                                         {"DataTime": "2025-07-24T13:00:00+08:00", "ElementValue": [{"RelativeHumidity": "72"}]}
#                                     ]
#                                 },
#                                 {
#                                     "ElementName": "風速",
#                                     "Time": [
#                                         {"DataTime": "2025-07-24T12:00:00+08:00", "ElementValue": [{"WindSpeed": "3.0"}]},
#                                         {"DataTime": "2025-07-24T13:00:00+08:00", "ElementValue": [{"WindSpeed": "2.5"}]}
#                                     ]
#                                 },
#                                 {
#                                     "ElementName": "風向",
#                                     "Time": [
#                                         {"DataTime": "2025-07-24T12:00:00+08:00", "ElementValue": [{"WindDirection": "北"}]},
#                                         {"DataTime": "2025-07-24T13:00:00+08:00", "ElementValue": [{"WindDirection": "東北"}]}
#                                     ]
#                                 },
#                                 {
#                                     "ElementName": "體感溫度",
#                                     "Time": [
#                                         {"DataTime": "2025-07-24T12:00:00+08:00", "ElementValue": [{"ApparentTemperature": "36"}]},
#                                         {"DataTime": "2025-07-24T13:00:00+08:00", "ElementValue": [{"ApparentTemperature": "37"}]}
#                                     ]
#                                 }
#                             ]
#                         }
#                     ]
#                 }
#             ]
#         }
#     }

#     hourly_data = parse_hourly_weather_elements(sample_json_data, location_name="臺中市")

#     if hourly_data:
#         print("\n解析後的逐小時天氣數據:")
#         for item in hourly_data:
#             print(item)
#     else:
#         print("未能解析天氣數據。")