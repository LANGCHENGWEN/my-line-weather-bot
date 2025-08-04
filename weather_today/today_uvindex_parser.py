# weather_today/today_uvindex_parser.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_uv_level_description(uv_index: int) -> str:
    """
    根據紫外線指數的數值，返回對應的風險等級描述。
    參考中央氣象署的紫外線指數分級：
    0-2: 低量級
    3-5: 中量級
    6-7: 高量級
    8-10: 過量級
    11+: 危險級
    """
    if uv_index >= 11:
        return "危險"
    elif uv_index >= 8:
        return "過量"
    elif uv_index >= 6:
        return "高"
    elif uv_index >= 3:
        return "中"
    elif uv_index >= 0:
        return "低"
    else:
        return "N/A" # 處理無效或預設值

def parse_uv_index(data: dict, target_station_id: str) -> dict | None:
    """
    解析從中央氣象局 O-A0005-001 API 獲取到的原始 JSON 資料，
    提取指定測站的每日紫外線指數最大值。

    :param data: 從中央氣象局 API 獲取到的原始 JSON 資料 (字典形式)。
    :param target_station_id: 要解析的目標測站 ID。
    :return: 包含指定測站紫外線指數的字典。如果資料不存在或測站未找到，
             則返回包含預設值的字典。
    """
    # 預設的回傳值，以便在找不到資料時直接使用
    default_data = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "StationID": target_station_id,
        "UVIndexRaw": -1, # 預設為 -1，代表無資料
        "UVIndexFormatted": "無資料"
    }

    if not data or "records" not in data or "weatherElement" not in data["records"]:
        logger.warning("傳入的紫外線數據無效或缺少必要鍵。")
        return default_data

    try:
        weather_element = data["records"]["weatherElement"]
        locations = weather_element.get("location", [])
        report_date = weather_element.get("Date") # 提取報告日期

        if not locations:
            logger.warning("紫外線數據中 'location' 列表為空或不存在。")
            return default_data

        for loc in locations:
            station_id = loc.get("StationID")
            uv_index = loc.get("UVIndex")
            
            if station_id == target_station_id:
                if uv_index is not None:
                    uv_index_int = int(uv_index) # 確保是整數
                    uv_level_description = get_uv_level_description(uv_index_int) # <-- 新增：獲取描述

                    # 將數字和文字描述組合成一個字串
                    uv_formatted_string = f"{uv_index_int} ({uv_level_description})"

                    parsed_uv_data = {
                        "Date": report_date,
                        "StationID": station_id,
                        "UVIndexRaw": uv_index_int, # 保留原始數值以供未來可能的需求
                        "UVIndexFormatted": uv_formatted_string  # 新增：紫外線等級描述
                    }
                    logger.info(f"成功解析測站 '{target_station_id}' 的紫外線指數。")
                    return parsed_uv_data
                else:
                    logger.warning(f"測站 '{target_station_id}' 的紫外線指數值為空。")
                    return default_data
        
        # 迴圈結束後仍未找到匹配的測站 ID
        logger.warning(f"在原始紫外線數據中未找到測站 ID '{target_station_id}' 的資料。")
        return default_data

    except KeyError as e:
        logger.error(f"解析紫外線數據時發生鍵錯誤: {e}")
        return default_data
    except Exception as e:
        logger.error(f"解析紫外線數據時發生未知錯誤: {e}")
        return default_data