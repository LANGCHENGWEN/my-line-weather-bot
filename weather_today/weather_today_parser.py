# weather_today/weather_today_parser.py
import logging
from collections import Counter
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def parse_today_weather(raw_data: dict, location_name: str) -> dict | None:
    """
    解析中央氣象署 F-C0032-001 的原始天氣資料，提取指定縣市今天的預報資訊。

    Args:
        raw_data (dict): 從 CWA API 取得的原始 JSON 資料。
        location_name (str): 欲解析的縣市名稱。

    Returns:
        dict | None: 包含今日天氣現象、降雨機率、最高溫、最低溫、舒適度指數、格式化溫度範圍的字典，
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
    
    # --- 日期和星期幾的格式化 ---
    today = datetime.now()
    date_formatted = today.strftime("%Y年%m月%d日")
    
    # 將星期幾的數字轉換為中文
    weekdays_chinese = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_chinese = weekdays_chinese[today.weekday()] # .weekday() 返回 0-6，0是星期一

    # 組合成你想要的格式
    full_date_string = f"日期：{date_formatted} ({weekday_chinese})"
    # --- 修改結束 ---

    parsed_weather = {
        "location_name": location_name,
        "date_full_formatted": full_date_string, # 今日日期
        "weather_phenomenon": "N/A",
        "max_temp_raw": -float('inf'), # 初始化為負無窮大以便找到最大值
        "min_temp_raw": float('inf'),  # 初始化為正無窮大以便找到最小值
        "formatted_temp_range": "N/A", # 帶有單位的格式化溫度範圍
        "pop_raw": 0, # 原始數字降雨機率，用於內部邏輯或傳遞給判斷層
        "pop_formatted": "0%", # 格式化後的降雨機率字串
        "comfort_index": "N/A"
    }

    # 初始化用於內部處理的溫度變數
    # min_t_val = "N/A"
    # max_t_val = "N/A"

    # 找到今天白天的預報時段 (假設為 06:00:00 - 18:00:00)
    # 或者取第一個時間區段作為"今日"的代表
    # 這裡的邏輯是找到第一個 startTime 屬於今天的時間段
    # today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 尋找與今天最相關的白天時段 (06:00-18:00)
    # 如果找不到，則取第一個可用的時段
    # target_time_period_data = {}

    today_date = datetime.now().date()

    all_weather_phenomena_today = [] # 新增：用來收集今天所有時段的天氣現象
    temp_comfort_index = []

    for element in target_location_data.get("weatherElement", []):
        element_name = element.get("elementName")
        
        for time_period in element.get("time", []):
            start_time_str = time_period.get("startTime")
            end_time_str = time_period.get("endTime") # 獲取結束時間用於判斷跨日
            
            if not start_time_str or not end_time_str:
                continue

            try:
                start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"日期時間格式不正確: {start_time_str} 或 {end_time_str}")
                continue

            # 判斷這個時間區段是否涵蓋今天
            # 如果開始時間是今天，或者開始時間是昨天晚上但結束時間是今天，都算今天
            is_relevant_today_period = (
                start_dt.date() == today_date or 
                (start_dt.date() == today_date - timedelta(days=1) and end_dt.date() == today_date)
            )
            # is_today = (start_dt.date() == datetime.now().date())
            # is_daytime_period = (start_dt.hour == 6 and start_dt.hour < 18)

            if is_relevant_today_period:
                param = time_period["parameter"]
                param_name = param.get("parameterName")
            # if is_today and is_daytime_period:
                # param_name = time_period["parameter"]["parameterName"]

                if element_name == "Wx":
                    if param_name:
                        all_weather_phenomena_today.append(param_name)

                elif element_name == "MaxT":
                    try:
                        current_max_t = int(param_name)
                        if current_max_t > parsed_weather["max_temp_raw"]:
                            parsed_weather["max_temp_raw"] = current_max_t
                    except (ValueError, TypeError):
                        pass # 忽略無效的溫度值

                elif element_name == "MinT":
                    try:
                        current_min_t = int(param_name)
                        if current_min_t < parsed_weather["min_temp_raw"]: # 尋找最小值
                            parsed_weather["min_temp_raw"] = current_min_t
                    except (ValueError, TypeError):
                        pass # 忽略無效的溫度值

                elif element_name == "PoP":
                    try:
                        current_pop = int(param_name)
                        if current_pop > parsed_weather["pop_raw"]: # 尋找最大降雨機率
                            parsed_weather["pop_raw"] = current_pop
                    except (ValueError, TypeError):
                        pass # 忽略無效的降雨機率值

                elif element_name == "CI":
                    if param_name and param_name not in temp_comfort_index:
                        temp_comfort_index.append(param_name)

    # --- 後處理和格式化 ---
    if all_weather_phenomena_today:
        wx_counts = Counter(all_weather_phenomena_today)
        # 找到次數最多的天氣現象，most_common(1) 返回一個列表，例如 [('多雲', 2)]
        most_common_wx = wx_counts.most_common(1)

        if most_common_wx:
            # 提取最常見的天氣現象名稱
            parsed_weather["weather_phenomenon"] = most_common_wx[0][0]
        else:
            parsed_weather["weather_phenomenon"] = "無資訊"
    else:
        parsed_weather["weather_phenomenon"] = "無資訊"

    # 處理降雨機率的格式化
    parsed_weather["pop_formatted"] = f"{parsed_weather['pop_raw']}%"

    # 處理溫度範圍的格式化
    if parsed_weather["min_temp_raw"] != float('inf') and parsed_weather["max_temp_raw"] != -float('inf'):
        parsed_weather["formatted_temp_range"] = f"{int(parsed_weather['min_temp_raw'])}°C ~ {int(parsed_weather['max_temp_raw'])}°C"
    else:
        parsed_weather["min_temp_raw"] = None # 如果沒找到有效溫度，將原始數值設為 None
        parsed_weather["max_temp_raw"] = None
        parsed_weather["formatted_temp_range"] = "N/A"

    # 處理舒適度指數
    if temp_comfort_index:
        # 簡單合併多個舒適度描述
        unique_ci = list(dict.fromkeys(temp_comfort_index))
        parsed_weather["comfort_index"] = "、".join(unique_ci)
    else:
        parsed_weather["comfort_index"] = "N/A"

    """
    # 在此處更新格式化的溫度範圍
    if min_t_val != "N/A" and max_t_val != "N/A":
        parsed_weather["formatted_temp_range"] = f"{min_t_val}°C ~ {max_t_val}°C"
        parsed_weather["min_temp"] = min_t_val # 原始數值也存起來，給穿搭邏輯用
        parsed_weather["max_temp"] = max_t_val # 同上
    else:
        parsed_weather["formatted_temp_range"] = "N/A"
        parsed_weather["min_temp"] = "N/A"
        parsed_weather["max_temp"] = "N/A"
    """

    """
    # 檢查核心數據是否齊全 (天氣現象、降雨機率、格式化溫度範圍)
    if parsed_weather["weather_phenomenon"] != "N/A" and \
       parsed_weather["pop"] != "N/A" and \
       parsed_weather["formatted_temp_range"] != "N/A":
        logger.info(f"成功解析 {location_name} 今日天氣資料。")
        return parsed_weather
    """

    # 最終檢查關鍵數據是否齊全
    required_keys = ["weather_phenomenon", "max_temp_raw", "min_temp_raw", "formatted_temp_range", "pop_raw", "comfort_index"]
    # missing_keys = [key for key in required_keys if parsed_weather[key] in ["N/A", "無資訊", 0] and not (key == "pop" and parsed_weather[key] == "0%")]
    """
    if all(parsed_weather[key] != "N/A" for key in required_keys):
        logger.info(f"成功解析 {location_name} 今日天氣資料。")
        return parsed_weather
    """
    
    # 如果未能找到所有數據，則在日誌中記錄哪些數據缺失
    # missing_keys = [key for key in required_keys if parsed_weather[key] == "N/A"]
    """
    if missing_keys:
        # 如果是 PoP 為 0% 就不算缺失
        if "pop" in missing_keys and parsed_weather["pop"] == "0%":
            missing_keys.remove("pop")
        if missing_keys: # 再次檢查是否還有缺失
            logger.warning(f"為 {location_name} 找到部分數據，但缺少關鍵資訊：{', '.join(missing_keys)}")
    """
        # 這裡你可以選擇返回部分數據，或返回 None
        # 如果你希望即使不完整也返回，則移除下面的 return None
        # 我建議在 Flex Message 處理 N/A 比較好，所以這裡返回 partial_data
        # 但如果數據太少沒意義，可以 return None
        # 對於穿搭建議，基礎數據 (溫度、天氣現象、降雨) 是必須的

    # 檢查核心數據是否為 'N/A', '無資訊', 或 None
    # 注意：pop_raw 預設為 0，如果為 0 則不視為缺失
    if any(parsed_weather[key] in ["N/A", "無資訊", None] for key in required_keys if not (key == "pop_raw" and parsed_weather[key] == 0)):
        logger.error(f"未能從 {location_name} 的資料中提取足夠的今日天氣資訊。缺失數據可能包括：{[k for k in required_keys if parsed_weather[k] in ['N/A', '無資訊', None]]}")
        return None

    """
    # 如果沒找到 06-18 時段，或者找不到今天任何時段，則嘗試拿第一個時段的資料
    # 這段是備用邏輯，確保即使預報時段不理想也能有數據
    if all(parsed_weather[key] == "N/A" for key in ["weather_phenomenon", "max_temp", "min_temp", "pop", "comfort_index", "formatted_temp_range"]):
        logger.warning(f"未能找到 {location_name} 今日白天預報時段，嘗試提取第一個預報時段的資料。")
        for element in target_location_data.get("weatherElement", []):
            element_name = element.get("elementName")
            if element.get("time"):
                first_time_period = element["time"][0]
                if element_name == "Wx":
                    parsed_weather["weather_phenomenon"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "MaxT":
                    max_t_val = first_time_period["parameter"]["parameterName"]
                elif element_name == "MinT":
                    min_t_val = first_time_period["parameter"]["parameterName"]
                elif element_name == "PoP":
                    parsed_weather["pop"] = first_time_period["parameter"]["parameterName"]
                elif element_name == "CI":
                    parsed_weather["comfort_index"] = first_time_period["parameter"]["parameterName"]

        # 在備用邏輯中也生成格式化的溫度範圍
        if min_t_val != "N/A" and max_t_val != "N/A":
            parsed_weather["formatted_temp_range"] = f"{min_t_val}°C ~ {max_t_val}°C"
        else:
            parsed_weather["formatted_temp_range"] = "N/A" # 確保在沒有找到時也設為N/A

        if all(parsed_weather[key] == "N/A" for key in ["weather_phenomenon", "max_temp", "min_temp", "pop", "comfort_index", "formatted_temp_range"]):
            logger.error(f"未能從 {location_name} 的資料中提取任何有效的今日天氣資訊。")
            return None
    """
    
    logger.info(f"解析 {location_name} 今日天氣資料完成。解析結果: {parsed_weather}")
    return parsed_weather