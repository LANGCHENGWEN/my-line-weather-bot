# weather_today/weather_today_parser.py
"""
解析中央氣象署「36 小時天氣預報」API (F-C0032-001) 的原始數據。
主要職責：
1. 數據提取：從複雜的 JSON 結構中，精確的找出指定縣市今天的預報資料。
2. 數據聚合：將分散在不同時間段和不同天氣元素中的數據（如天氣現象、溫度、降雨機率）進行整合。
3. 數據格式化：將原始的數值和代碼轉換成更具可讀性的格式，例如將日期轉換為「年/月/日 (星期幾)」，將溫度範圍組合成一個字串。
4. 錯誤處理與回退：處理數據缺失、格式不符或找不到指定縣市等各種例外情況，並在發現問題時返回 None，確保程式的穩定性。
"""
import logging
from collections import Counter
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- 解析從中央氣象署 API 獲取到的原始 JSON 數據 ---
def parse_today_weather(raw_data: dict, location_name: str) -> dict | None:
    """
    解析中央氣象署 F-C0032-001 的原始天氣資料，提取指定縣市今天的預報資訊。
    進行多層次的檢查與處理：首先驗證原始數據的有效性，接著定位到目標縣市的數據，然後遍歷每個天氣元素和時間段，收集所有與「今天」相關的資訊。
    最後對收集到的數據進行後處理，例如計算溫度範圍、確定主要天氣現象，並將結果打包成一個易於使用的字典。

    Args:
        raw_data (dict): 從 CWA API 取得的原始 JSON 資料。
        location_name (str): 縣市名稱。

    Returns:
        dict | None: 包含 36 小時天氣數據的字典，如果資料解析失敗或找不到指定縣市，則返回 None。
    """
    # 檢查 `"records"` 和 `"location"` 鍵是否存在
    if not raw_data or "records" not in raw_data or "location" not in raw_data["records"]:
        logger.warning("原始資料格式不正確或缺少 'records' / 'location' 鍵。")
        return None

    # 檢查 `"location"` 列表是否為空
    if not raw_data["records"]["location"]:
        logger.warning(f"原始資料中 'location' 列表為空，沒有 {location_name} 的數據。")
        return None

    # --- 在 JSON 結構中，找到與 `location_name` 相匹配的數據 ---
    """
    遍歷 `raw_data` 中的所有地點（location）。
    一旦找到匹配的 `'locationName'`，就會將該數據賦值給 `target_location_data` 並立即跳出迴圈。
    """
    target_location_data = None
    for loc_data in raw_data["records"]["location"]:
        if loc_data.get("locationName") == location_name:
            target_location_data = loc_data
            break # 找到目標地點後就停止遍歷

    if not target_location_data:
        logger.warning(f"在資料中找不到 {location_name} 的天氣資訊。")
        return None
    
    # --- 日期和星期幾的格式化 ---
    today = datetime.now() # 獲取當前日期
    date_formatted = today.strftime("%Y年%m月%d日") # 格式化為「年/月/日」
    
    # 將 0-6 的數字轉換為中文的星期幾
    weekdays_chinese = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_chinese = weekdays_chinese[today.weekday()] # .weekday() 返回 0-6，0 是星期一

    # 組合成一個完整的日期字串
    full_date_string = f"日期：{date_formatted} ({weekday_chinese})"

    # --- 初始化結果字典 ---
    """
    初始化一個字典 `parsed_weather`，用於存放最終解析出的天氣數據。
    初始化時為每個鍵設定了預設值，例如「無資料」或數值的極值（`float('inf')`）。
    確保即使在某些數據缺失的情況下，字典的結構也保持一致，避免後續的 `KeyError`。
    """
    parsed_weather = {
        "location_name"        : location_name,
        "date_full_formatted"  : full_date_string,
        "weather_phenomenon"   : "無資料",
        "max_temp_raw"         : -float('inf'), # 初始化為負無窮大以便找到最大值
        "min_temp_raw"         : float('inf'),  # 初始化為正無窮大以便找到最小值
        "formatted_temp_range" : "無資料",
        "pop_raw"              : 0,             # 原始數字降雨機率，用於內部邏輯或傳遞給判斷層
        "pop_formatted"        : "無資料",
        "comfort_index"        : "無資料"
    }

    # --- 收集今日所有相關時段的數據 ---
    """
    特別考慮「跨夜時段」和「午夜後查詢」的邊界情況，確保無論用戶何時查詢，都能獲取到當天最相關的數據，而不是只取第一個時段。
    """
    today_date = datetime.now().date()

    # 儲存所有與「今日」相關的數據
    main_period_data = {
        "Wx"   : [],
        "MinT" : [],
        "MaxT" : [],
        "PoP"  : [],
        "CI"   : []
    }

    # 遍歷目標地點下的每個天氣元素 (`element`)
    for element in target_location_data.get("weatherElement", []):
        element_name = element.get("elementName")
        
        # 遍歷目標地點下的每個時間段 (`time_period`)
        for time_period in element.get("time", []):
            start_time_str = time_period.get("startTime")
            end_time_str = time_period.get("endTime") # 獲取結束時間用於判斷跨日
            
            if not start_time_str or not end_time_str:
                continue

            # 確保日期時間資料是正確的格式
            try:
                start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"日期時間格式不正確: {start_time_str} 或 {end_time_str}")
                continue

            current_hour = datetime.now().hour # 獲取當前小時數，以便判斷是否臨近午夜
            period_date = start_dt.date()      # 單獨提取出日期部分，而不需要考慮時間、分鐘或秒數

            # 判斷時間區段是否涵蓋今天
            # 第一個條件：時段開始於今天，或者開始於昨天但結束於今天（跨夜時段）
            is_relevant_today_period = (
                period_date == today_date or 
                (period_date == today_date - timedelta(days=1) and end_dt.date() == today_date)
            )

            # 第二個條件：如果當前時間非常接近午夜 (例如 23 點後)，並且時段開始於明天凌晨
            # 這個條件是為了確保在午夜前後查詢時，能正確取到最近的有效數據
            is_tomorrow_early_morning_but_relevant = (
                current_hour >= 23 and period_date == today_date + timedelta(days=1) and start_dt.hour < 6
            )

            # 檢查時間區段是否與今天或明天凌晨相關，如果條件符合，就提取出這個時間區段相關的參數名稱
            if is_relevant_today_period or is_tomorrow_early_morning_but_relevant:
                param = time_period["parameter"]
                param_name = param.get("parameterName")

                if element_name == "Wx" and param_name:
                    main_period_data["Wx"].append(param_name)

                elif element_name == "MaxT":
                    try:
                        main_period_data["MaxT"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的最高溫度值

                elif element_name == "MinT":
                    try:
                        main_period_data["MinT"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的最低溫度值

                elif element_name == "PoP":
                    try:
                        main_period_data["PoP"].append(int(param_name))
                    except (ValueError, TypeError):
                        pass # 忽略無效的降雨機率

                elif element_name == "CI" and param_name:
                    main_period_data["CI"].append(param_name)

    # --- 後處理和格式化 ---
    """
    將前面收集到的原始數據列表，轉換成最終需要的格式。
    """
    # 使用 `Counter` 統計天氣現象出現的次數，並選出最常見的一個作為主要天氣現象
    if main_period_data["Wx"]:
        wx_counts = Counter(main_period_data["Wx"])
        parsed_weather["weather_phenomenon"] = wx_counts.most_common(1)[0][0]
    else:
        parsed_weather["weather_phenomenon"] = "無資料"

    # 處理降雨機率的格式化，取所有時段中的最大值
    if main_period_data["PoP"]:
        parsed_weather["pop_raw"] = max(main_period_data["PoP"])
    else:
        parsed_weather["pop_raw"] = 0 # 沒有降雨機率就設為 0
    parsed_weather["pop_formatted"] = f"{parsed_weather['pop_raw']}%"

    # 從所有時段的最高溫和最低溫中，分別找出最大值和最小值，然後組合成一個格式化的溫度範圍字串
    if main_period_data["MinT"] and main_period_data["MaxT"]:
        parsed_weather["min_temp_raw"] = min(main_period_data["MinT"])
        parsed_weather["max_temp_raw"] = max(main_period_data["MaxT"])
        parsed_weather["formatted_temp_range"] = f"{parsed_weather['min_temp_raw']}°C ~ {parsed_weather['max_temp_raw']}°C"
    else:
        parsed_weather["min_temp_raw"] = None # 如果沒找到有效溫度，將原始數值設為 None
        parsed_weather["max_temp_raw"] = None
        parsed_weather["formatted_temp_range"] = "無資料"

    # 處理舒適度指數，合併所有不重複的描述
    if main_period_data["CI"]:
        unique_ci = list(dict.fromkeys(main_period_data["CI"]))
        parsed_weather["comfort_index"] = "、".join(unique_ci)
    else:
        parsed_weather["comfort_index"] = "無資料"

    # --- 最終數據完整性檢查 ---
    # 定義一個 `required_keys` 列表，包含所有最核心的數據
    required_keys = ["weather_phenomenon", "max_temp_raw", "min_temp_raw", "formatted_temp_range", "pop_raw", "comfort_index"]
    missing_data_found = False
    missing_keys_list = []

    # 遍歷上面數據的鍵，檢查對應的值是否為無效的預設值
    for key in required_keys:
        # 如果是 pop_raw 且值為 0，不視為缺失
        if key == "pop_raw" and parsed_weather[key] == 0:
            continue
        # 如果值是 "N/A", "無資料", None, 或預設的極值，則視為缺失
        if parsed_weather[key] in ["N/A", "無資料", None] or \
           (key == "max_temp_raw" and parsed_weather[key] == -float('inf')) or \
           (key == "min_temp_raw" and parsed_weather[key] == float('inf')):
            missing_data_found = True
            missing_keys_list.append(key)

    # 檢查核心數據是否為 'N/A', '無資料', 或 None
    if missing_data_found:
        logger.error(f"未能從 {location_name} 的資料中提取足夠的今日天氣資訊。缺失數據可能包括：{missing_keys_list}")
        return None
    
    logger.info(f"解析 {location_name} 今日天氣資料完成。解析結果: {parsed_weather}")
    return parsed_weather