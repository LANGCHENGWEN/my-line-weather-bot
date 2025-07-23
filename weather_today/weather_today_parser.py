# weather_today/weather_today_parser.py
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def parse_today_weather(raw_data: dict, location_name: str) -> dict | None:
    """
    解析中央氣象署 F-C0032-001 的原始天氣資料，提取指定縣市今天的預報資訊。

    Args:
        raw_data (dict): 從 CWA API 取得的原始 JSON 資料。
        location_name (str): 欲解析的縣市名稱。

    Returns:
        dict | None: 包含今日天氣現象、降雨機率、最低溫、最高溫、舒適度指數的字典，
                     如果資料解析失敗或找不到指定縣市，則返回 None。
    """
    if not raw_data or "records" not in raw_data or "location" not in raw_data["records"]:
        logger.warning("原始資料格式不正確或缺少 'records' / 'location' 鍵。")
        return None
    
    # *** 新增這行檢查：如果 location 列表是空的，直接返回 None ***
    if not raw_data["records"]["location"]:
        logger.warning(f"原始資料中 'location' 列表為空，沒有 {location_name} 的數據。")
        return None

    target_location_data = None
    for loc_data in raw_data["records"]["location"]:
        if loc_data.get("locationName") == location_name:
            target_location_data = loc_data
            break

    if not target_location_data:
        logger.warning(f"在資料中找不到 {location_name} 的天氣資訊。")
        return None

    parsed_weather = {
        "location_name": location_name,
        "date": datetime.now().strftime("%Y年%m月%d日"), # 今日日期
        "weekday": datetime.now().strftime("%w"), # 0-6 代表星期日-星期六
        "time": datetime.now().strftime("%H:%M"), # 當前時間
        "weather_phenomenon": "N/A",
        "pop": "N/A",
        "min_temp": "N/A",
        "max_temp": "N/A",
        "comfort_index": "N/A"
    }

    # 找到今天白天的預報時段 (假設為 06:00:00 - 18:00:00)
    # 或者取第一個時間區段作為"今日"的代表
    # 這裡的邏輯是找到第一個 startTime 屬於今天的時間段
    # today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 尋找與今天最相關的白天時段 (06:00-18:00)
    # 如果找不到，則取第一個可用的時段
    # target_time_period_data = {}

    for element in target_location_data.get("weatherElement", []):
        element_name = element.get("elementName")
        
        for time_period in element.get("time", []):
            start_time_str = time_period.get("startTime")
            end_time_str = time_period.get("endTime")
            
            if not start_time_str or not end_time_str:
                continue

            try:
                start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"日期時間格式不正確: {start_time_str} 或 {end_time_str}")
                continue

            # 判斷是否為「今天」的時段 (簡單判斷開始日期是否是今天)
            # 優先找今天白天的預報 (06-18)
            is_today = (start_dt.date() == datetime.now().date())
            is_daytime_period = (start_dt.hour == 6 and end_dt.hour == 18)

            if is_today and is_daytime_period:
                if element_name == "Wx":
                    parsed_weather["weather_phenomenon"] = time_period["parameter"]["parameterName"]
                elif element_name == "PoP":
                    parsed_weather["pop"] = time_period["parameter"]["parameterName"]
                elif element_name == "MinT":
                    parsed_weather["min_temp"] = time_period["parameter"]["parameterName"]
                elif element_name == "MaxT":
                    parsed_weather["max_temp"] = time_period["parameter"]["parameterName"]
                elif element_name == "CI":
                    parsed_weather["comfort_index"] = time_period["parameter"]["parameterName"]
                
                # 如果所有關鍵數據都找到了，可以提前返回
                if all(parsed_weather[key] != "N/A" for key in ["weather_phenomenon", "pop", "min_temp", "max_temp", "comfort_index"]):
                    logger.info(f"成功解析 {location_name} 今日天氣資料。")
                    return parsed_weather

    # 如果沒找到 06-18 時段，或者找不到今天任何時段，則嘗試拿第一個時段的資料
    # 這段是備用邏輯，確保即使預報時段不理想也能有數據
    if all(parsed_weather[key] == "N/A" for key in ["weather_phenomenon", "pop", "min_temp", "max_temp", "comfort_index"]):
        logger.warning(f"未能找到 {location_name} 今日白天預報時段，嘗試提取第一個預報時段的資料。")
        for element in target_location_data.get("weatherElement", []):
            element_name = element.get("elementName")
            if element.get("time"):
                first_time_period = element["time"][0]
                if element_name == "Wx":
                    parsed_weather["weather_phenomenon"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "PoP":
                    parsed_weather["pop"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "MinT":
                    parsed_weather["min_temp"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "MaxT":
                    parsed_weather["max_temp"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "CI":
                    parsed_weather["comfort_index"] = first_time_period["parameter"]["parameterName"]

        if all(parsed_weather[key] == "N/A" for key in ["weather_phenomenon", "pop", "min_temp", "max_temp", "comfort_index"]):
            logger.error(f"未能從 {location_name} 的資料中提取任何有效的今日天氣資訊。")
            return None
    
    logger.info(f"解析 {location_name} 今日天氣資料完成。")
    return parsed_weather