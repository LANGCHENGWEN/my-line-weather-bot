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
        "weather_phenomenon": "無資料",
        "max_temp_raw": -float('inf'), # 初始化為負無窮大以便找到最大值
        "min_temp_raw": float('inf'),  # 初始化為正無窮大以便找到最小值
        "formatted_temp_range": "無資料", # 帶有單位的格式化溫度範圍
        "pop_raw": 0, # 原始數字降雨機率，用於內部邏輯或傳遞給判斷層
        "pop_formatted": "無資料", # 格式化後的降雨機率字串
        "comfort_index": "無資料"
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

    # all_weather_phenomena_today = [] # 新增：用來收集今天所有時段的天氣現象
    # temp_comfort_index = []

    # 增加一個變數來追蹤是否已經找到當天的主要時段
    # found_main_today_period = False

    # 儲存主要時段的數據，如果找到的話
    main_period_data = {
        "Wx": [],
        "MinT": [],
        "MaxT": [],
        "PoP": [],
        "CI": []
    }

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

            # 獲取當前小時數，以便判斷是否臨近午夜
            current_hour = datetime.now().hour

            # 時段日期
            period_date = start_dt.date()

            # 判斷這個時間區段是否涵蓋今天
            # 如果開始時間是今天，或者開始時間是昨天晚上但結束時間是今天，都算今天

            # 第一個條件：時段開始於今天，或者開始於昨天但結束於今天（跨夜時段）
            # 這個邏輯通常用於處理「今日」的全貌，包含早、中、晚
            is_relevant_today_period = (
                period_date == today_date or 
                (period_date == today_date - timedelta(days=1) and end_dt.date() == today_date)
            )
            # is_today = (start_dt.date() == datetime.now().date())
            # is_daytime_period = (start_dt.hour == 6 and start_dt.hour < 18)

            # 第二個條件：如果當前時間非常接近午夜 (例如 23 點後)，並且時段開始於明天凌晨，也納入考慮
            # 這個條件是為了確保在午夜前後查詢時，能正確取到最近的有效數據
            is_tomorrow_early_morning_but_relevant = (
                current_hour >= 23 and period_date == today_date + timedelta(days=1) and start_dt.hour < 6
            )

            if is_relevant_today_period or is_tomorrow_early_morning_but_relevant:
                param = time_period["parameter"]
                param_name = param.get("parameterName")
            # if is_today and is_daytime_period:
                # param_name = time_period["parameter"]["parameterName"]

                if element_name == "Wx" and param_name:
                    main_period_data["Wx"].append(param_name)

                elif element_name == "MaxT":
                    try:
                        main_period_data["MaxT"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的溫度值

                elif element_name == "MinT":
                    try:
                        main_period_data["MinT"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的溫度值

                elif element_name == "PoP":
                    try:
                        main_period_data["PoP"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的降雨機率值

                elif element_name == "CI" and param_name:
                    main_period_data["CI"].append(param_name)

    # --- 後處理和格式化 ---
    if main_period_data["Wx"]:
        wx_counts = Counter(main_period_data["Wx"])
        # 找到次數最多的天氣現象，most_common(1) 返回一個列表，例如 [('多雲', 2)]
        parsed_weather["weather_phenomenon"] = wx_counts.most_common(1)[0][0]
    else:
        parsed_weather["weather_phenomenon"] = "無資料"

    # 處理降雨機率的格式化
    if main_period_data["PoP"]:
        # 降雨機率取所有相關時段中的最大值
        parsed_weather["pop_raw"] = max(main_period_data["PoP"])
    else:
        parsed_weather["pop_raw"] = 0 # 沒有降雨機率就設為 0
    parsed_weather["pop_formatted"] = f"{parsed_weather['pop_raw']}%"

    # 處理溫度範圍的格式化
    if main_period_data["MinT"] and main_period_data["MaxT"]:
        parsed_weather["min_temp_raw"] = min(main_period_data["MinT"])
        parsed_weather["max_temp_raw"] = max(main_period_data["MaxT"])
        parsed_weather["formatted_temp_range"] = f"{parsed_weather['min_temp_raw']}°C ~ {parsed_weather['max_temp_raw']}°C"
    else:
        parsed_weather["min_temp_raw"] = None # 如果沒找到有效溫度，將原始數值設為 None
        parsed_weather["max_temp_raw"] = None
        parsed_weather["formatted_temp_range"] = "無資料"

    # 處理舒適度指數
    if main_period_data["CI"]:
        # 簡單合併多個舒適度描述
        unique_ci = list(dict.fromkeys(main_period_data["CI"]))
        parsed_weather["comfort_index"] = "、".join(unique_ci)
    else:
        parsed_weather["comfort_index"] = "無資料"

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

    # 最終檢查關鍵數據是否齊全 (將 PoP 的 0 排除在「缺失」之外)
    required_keys = ["weather_phenomenon", "max_temp_raw", "min_temp_raw", "formatted_temp_range", "pop_raw", "comfort_index"]
    # missing_keys = [key for key in required_keys if parsed_weather[key] in ["N/A", "無資訊", 0] and not (key == "pop" and parsed_weather[key] == "0%")]
    missing_data_found = False
    missing_keys_list = []
    for key in required_keys:
        # 如果是 pop_raw 且其值為 0，則不視為缺失
        if key == "pop_raw" and parsed_weather[key] == 0:
            continue
        # 其他情況下，如果值是 "N/A", "無資料", None, 或是預設的極值，則視為缺失
        if parsed_weather[key] in ["N/A", "無資料", None] or \
           (key == "max_temp_raw" and parsed_weather[key] == -float('inf')) or \
           (key == "min_temp_raw" and parsed_weather[key] == float('inf')):
            missing_data_found = True
            missing_keys_list.append(key)
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
    if missing_data_found:
        logger.error(f"未能從 {location_name} 的資料中提取足夠的今日天氣資訊。缺失數據可能包括：{missing_keys_list}")
        return None
    
    logger.info(f"解析 {location_name} 今日天氣資料完成。解析結果: {parsed_weather}")
    return parsed_weather


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