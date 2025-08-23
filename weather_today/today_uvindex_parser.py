# weather_today/today_uvindex_parser.py
"""
解析從中央氣象署獲取的紫外線指數原始數據。
主要職責：
1. 定義紫外線分級：根據數值將紫外線指數轉換為易於理解的風險等級描述（如「高」、「危險」等）。
2. 解析數據：從複雜的 JSON 數據結構中，找出指定測站的紫外線指數值。
3. 數據清理與格式化：將原始的數值轉換為帶有描述的格式化字串，並處理資料缺失或無效的情況。
4. 錯誤回退：如果在解析過程中遇到任何問題（例如找不到測站或鍵值），返回一個包含預設值的字典，確保程式不會因此崩潰。
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# --- 根據紫外線指數的數值，返回對應的風險等級描述 ---
def get_uv_level_description(uv_index: int) -> str:
    """
    使用 `if/elif` 條件語句判斷輸入的數值屬於哪個等級，並返回相應的中文描述。

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
        return "無資料" # 處理無效或預設值

# --- 解析從中央氣象署 O-A0005-001 API 獲取到的原始 JSON 資料 ---
def parse_uv_index(data: dict, target_station_id: str) -> dict | None:
    """
    提取指定測站的每日紫外線指數最大值。
    這個函式是數據解析的核心，遍歷 API 回應中的測站列表，尋找指定的測站 ID。
    提取紫外線指數值並呼叫 `get_uv_level_description` 函式進行格式化。
    包含多層次的錯誤檢查，確保即使在數據不完整或格式錯誤時，程式也能穩定運行。

    Args:
        data (dict): 從中央氣象署 API 獲取到的原始 JSON 資料。
        target_station_id (str): 要解析的目標測站 ID。

    Returns:
        dict: 指定測站紫外線指數的字典；如果資料不存在或測站未找到，則返回包含預設值的字典。
    """
    # 預設回傳值與前置檢查
    # 定義一個 `default_data` 字典，作為找不到數據或發生錯誤時的回退值
    default_data = {
        "Date"             : datetime.now().strftime("%Y-%m-%d"),
        "StationID"        : target_station_id,
        "UVIndexRaw"       : -1, # 預設為 -1，代表無資料
        "UVIndexFormatted" : "無資料"
    }

    # 進行數據有效性檢查，如果傳入的數據無效或缺少必要的鍵，會發出警告並直接返回這個預設值，避免後續運行時的錯誤
    if not data or "records" not in data or "weatherElement" not in data["records"]:
        logger.warning("傳入的紫外線數據無效或缺少必要鍵。")
        return default_data

    try:
        # 從原始數據中提取「氣象元素」（`weatherElement`）和「地點」（`location`）列表
        weather_element = data["records"]["weatherElement"]
        locations = weather_element.get("location", [])
        report_date = weather_element.get("Date")

        if not locations:
            logger.warning("紫外線數據中 'location' 列表為空或不存在。")
            return default_data

        # 遍歷每個地點，檢查 `StationID` 是否與尋找的目標匹配
        for loc in locations:
            station_id = loc.get("StationID")
            uv_index = loc.get("UVIndex")
            
            # 如果匹配成功，提取紫外線指數值，並呼叫 `get_uv_level_description` 轉換為描述
            if station_id == target_station_id:
                if uv_index is not None:
                    uv_index_int = int(uv_index) # 確保是整數
                    uv_level_description = get_uv_level_description(uv_index_int)

                    # 將數字和文字描述組合成一個字串
                    uv_formatted_string = f"{uv_index_int} ({uv_level_description})"

                    parsed_uv_data = {
                        "Date"             : report_date,
                        "StationID"        : station_id,
                        "UVIndexRaw"       : uv_index_int,        # 保留原始數值以供未來可能的需求
                        "UVIndexFormatted" : uv_formatted_string  # 紫外線等級描述
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