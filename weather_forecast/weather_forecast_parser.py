# weather_forecast/weather_forecast_parser.py
"""
解析中央氣象署 API 回傳的「F-D0047-091」天氣預報原始數據。
主要職責：
1. 從複雜的 JSON 數據中，提取出指定縣市的預報資訊。
2. 將每個天氣元素（如溫度、降雨機率）按照時間段進行聚合。
3. 根據時段（白天或夜晚）將數據分組。
4. 最終將處理後的數據整理成一個結構化且易於程式碼後續使用的字典格式，供 Flex Message 格式化模組使用。
"""
import json
import logging
import datetime

logger = logging.getLogger(__name__)

def safe_val(val):
    """
    確保如果 API 回傳的值為 None、"-", 或空字串時，將其替換為 "無資料"。
    避免在後續處理中因數據缺失而引發錯誤，同時提供一個友善的顯示值。
    """
    return "無資料" if val in [None, "-", ""] else val

# --- 將中央氣象署 API 中文名稱的氣象元素名稱，對應到程式碼中更易於使用的英文鍵名 ---
"""
例如 `"最高溫度"` 對應到內部的 `("max_temp", "MaxTemperature")`。
`"max_temp"` 是自己定義的輸出鍵，而 `"MaxTemperature"` 是 API 數據中實際的鍵名。
"""
element_field_map = {
    "天氣現象" : ("weather_desc", "Weather"),
    "最高溫度" : ("max_temp", "MaxTemperature"),
    "最高體感溫度" : ("max_feel", "MaxApparentTemperature"),
    "最低溫度" : ("min_temp", "MinTemperature"),
    "最低體感溫度" : ("min_feel", "MinApparentTemperature"),
    "平均相對濕度" : ("humidity", "RelativeHumidity"),
    "12小時降雨機率" : ("pop", "ProbabilityOfPrecipitation"),
    "風速" : ("wind_speed", "WindSpeed"),
    "風向" : ("wind_dir", "WindDirection"),
    "最大舒適度指數" : ("comfort_max", "MaxComfortIndexDescription"),
    "最小舒適度指數" : ("comfort_min", "MinComfortIndexDescription"),
    "紫外線指數" : ("uv_index", "UVIndex")
}

# --- 判斷給定的日期是否為週末 (週六或週日) ---
def is_weekend(date_obj: datetime.date) -> bool:
    """
    使用 weekday() 方法，返回值 0 代表星期一，5 代表星期六，6 代表星期日。
    只要返回值大於等於 5，就表示是週末。
    """
    return date_obj.weekday() >= 5

# --- 根據給定日期與今天的關係，回傳「今天」、「明天」或格式化的日期字串 ---
def get_date_prefix(date_obj: datetime.date) -> str:
    """
    生成友善的日期顯示，讓用戶可以一目了然的知道預報是哪一天。
    """
    current_date = datetime.datetime.now().date()
    if date_obj == current_date:
        return "今天"
    elif date_obj == current_date + datetime.timedelta(days=1):
        return "明天"
    else:
        return date_obj.strftime("%m/%d") # 使用 strftime 格式化日期，例如 `07/03`

# --- 解析中央氣象署「F-D0047-091」資料 (未來一週天氣預報) ---
def parse_forecast_weather(cwa_raw_data: dict, city_name: str) -> dict:
    """
    整個解析流程的主體，遍歷原始 API 數據，提取出指定縣市的所有氣象元素。
    將這些元素按日期和時段（白天/夜晚）進行聚合，最終整理成一個乾淨的字典。
    
    Args:
        cwa_raw_data (dict): 原始 API 回傳 JSON。
        city_name (str): 要查詢的縣市名稱，例如 "臺中市"。

    Returns:
        dict: 解析後的天氣資料結構，含多個時間段的預報。
    """
    logger.debug(f"進入 parse_forecast_weather 函式，正在處理地點: {city_name}")

    # 數據類型檢查
    # 確保傳入的 `cwa_raw_data` 是一個有效的字典；如果不是，則記錄錯誤並返回一個空字典，防止程式崩潰
    if not isinstance(cwa_raw_data, dict):
        logger.error(f"cwa_raw_data 不是有效的字典類型: {type(cwa_raw_data)}")
        return {"location_name": city_name, "forecast_periods": []}

    logger.debug(f"實際取得的 CWA JSON 結構: {json.dumps(cwa_raw_data, indent=2, ensure_ascii=False)[:2000]}...")
    
    parsed_weather = {}

    # 提取目標地點的數據
    """
    從多層嵌套的 API 數據結構中，精確的找到目標縣市的資料。
    API 數據結構為 `records` -> `Locations` -> `Location`。
    遍歷所有的 `Location`，直到找到 `LocationName` 與 `city_name` 相符的那一個。
    確保只處理我們需要的數據。
    """
    records = cwa_raw_data.get("records", {})
    if not records:
        logger.error("CWA API 資料中缺少 'records' 或其為空。")
        return {}
    
    locations = records.get("Locations", [])
    if not locations:
        logger.error("CWA API 資料中缺少 'Locations' 或其為空。")
        return {}
    
    all_locations = locations[0].get("Location", [])
    if not all_locations:
        logger.error("Locations 中缺少 'Location'。")
        return {}

    # 列出所有 LocationName，方便 debug
    location_names = [loc.get("LocationName") for loc in all_locations]
    logger.debug(f"可用 LocationName 清單: {location_names}")

    # 遍歷所有的 `Location`
    target_location = None
    for loc in all_locations:
        if loc.get("LocationName") == city_name:
            target_location = loc
            break

    if not target_location:
        logger.warning(f"找不到指定縣市 '{city_name}' 的資料。")
        return {}
    
    logger.info(f"✅ 成功找到縣市 {city_name} 的資料")
    logger.info(f"共取得 {len(target_location['WeatherElement'])} 個氣象元素")
    logger.debug(f"📦 target_location 內容: {json.dumps(target_location, ensure_ascii=False, indent=2)}")

    # 列出找到的天氣元素，以及每個元素有多少個時間段的預報數據，方便 debug
    for el in target_location["WeatherElement"]:
        logger.info(f"元素 {el['ElementName']} 有 {len(el['Time'])} 筆時間段")

    # 聚合時間段資料
    daily_aggregated = {}

    # 遍歷從氣象署 API 獲取的所有天氣元素
    for element in target_location.get("WeatherElement", []):
        element_name = element.get("ElementName")
        logger.debug(f"➡️ 目前 ElementName：{element_name}")
        # 檢查當前的天氣元素名稱（例如 天氣現象 或 最高溫度）是否在我們定義的 element_field_map 字典中
        if element_name not in element_field_map:
            logger.debug(f"ElementName: {element_name} 不在 element_field_map 中。跳過。")
            continue # 如果不在，程式直接跳過，進入下一個天氣元素

        # 取出自己定義的輸出鍵（target_key，例如 max_temp）和 API 數據中的實際鍵名（inner_field，例如 MaxTemperature）
        target_key, inner_field = element_field_map[element_name]
        logger.debug(f"ElementName: {element_name}, 對應輸出鍵: {target_key}, 內部取值鍵: {inner_field}")

        times_data = element.get("Time", [])
        # 檢查當前天氣元素是否有任何相關的時間數據
        if not times_data:
            logger.debug(f"ElementName: {element_name} 沒有 Time 數據。跳過。")
            continue # 如果沒有，直接跳過

        # 遍歷當前天氣元素下的所有時間段
        for time_entry in element.get("Time", []):
            start_time = time_entry.get("StartTime")
            end_time = time_entry.get("EndTime")

            if not start_time or not end_time:
                logger.warning(f"時間資訊不完整，跳過該筆 time_entry: {time_entry}")
                continue

            # 判斷時段是白天或夜晚
            """
            白天時段：從早上 6 點到下午 6 點（`>= 6 and < 18`）。
            夜晚時段：從下午 6 點到隔天早上 6 點（`>= 18 or < 6`）。
            將同一天的白天和夜晚數據分開儲存，方便後續顯示。
            每個時段的數據都被儲存到 `daily_aggregated` 字典中，並以日期作為鍵。
            """
            try:
                start_dt = datetime.datetime.fromisoformat(start_time) # 將時間字串轉換為 datetime 物件
                start_dt_no_tz = start_dt.replace(tzinfo=None)
            except ValueError as e:
                logger.error(f"解析時間字串失敗: {start_time} 或 {end_time}. 錯誤: {e}")
                continue

            # 判斷 day 或 night
            period = "unknown"
            if start_dt_no_tz.hour >= 6 and start_dt_no_tz.hour < 18:
                period = "day"
                date_key = start_dt_no_tz.date().isoformat()
            elif start_dt_no_tz.hour >= 18 or start_dt_no_tz.hour < 6:
                period = "night"
                date_key = start_dt_no_tz.date().isoformat()
            else:
                logger.warning(f"無法判斷時段屬於白天或夜晚，StartTime: {start_time}. 歸類為 unknown.")
                date_key = start_dt_no_tz.date().isoformat() # 即使未知也給個日期

            # 初始化該時間段的數據
            if date_key not in daily_aggregated:
                daily_aggregated[date_key] = {
                    "date"             : date_key,
                    "is_weekend"       : is_weekend(datetime.date.fromisoformat(date_key)),
                    "date_prefix"      : get_date_prefix(datetime.date.fromisoformat(date_key)),
                    "date_str"         : "",
                    "date_obj"         : datetime.date.fromisoformat(date_key),
                    "start_time_day"   : None,
                    "end_time_day"     : None,
                    "start_time_night" : None,
                    "end_time_night"   : None
                }
                logger.debug(f"新增日期 {date_key}，是否週末: {daily_aggregated[date_key]['is_weekend']}")

            # 根據 `element_field_map` 的定義，從 `ElementValue` 字典中取出對應的值
            value_dict = time_entry.get("ElementValue", [{}])[0]
            # 使用 `safe_val` 函式處理缺失數據
            val = safe_val(value_dict.get(inner_field))

            logger.debug(f"📅 處理元素: {element_name} / Start: {start_time} / End: {end_time} / Period: {period} / date_key: {date_key} / inner_field: {inner_field}")
            logger.debug(f"ElementValue: {value_dict} / 取值結果: {val}")

            # 將數值存入正確的 key 中
            daily_aggregated[date_key][f"{target_key}_{period}"] = val

            # 記錄原始時間字串，用於後續填充 Flex Message
            if period == "day":
                daily_aggregated[date_key]["start_time_day"] = start_time
                daily_aggregated[date_key]["end_time_day"] = end_time
            elif period == "night":
                daily_aggregated[date_key]["start_time_night"] = start_time
                daily_aggregated[date_key]["end_time_night"] = end_time
            else:
                 logger.warning(f"未知時段的 StartTime/EndTime: {start_time} / {end_time}")

    # 將前面聚合的 `daily_aggregated` 字典轉換為一個列表
    """
    先對字典的鍵（日期字串）進行排序，確保預報的順序是正確的。
    然後遍歷排序後的日期，將每個日期的數據字典添加到列表中。
    在這個過程中，會將日期轉換成更友善的中文格式（例如「2025年7月2日 (二)」）。
    """
    forecast_periods = []

    for date_key in sorted(daily_aggregated.keys()):
        daily = daily_aggregated[date_key]

        if daily["date_obj"]:
            weekday_map_chinese = {
                0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"
            }
            chinese_weekday = weekday_map_chinese.get(daily["date_obj"].weekday(), "")

            # 格式化完整日期字串
            # 使用 try-except 區塊處理不同作業系統下 strftime 格式字串的差異
            # 確保程式碼在 Windows 和 Linux/MacOS 上都能正常運作
            try:
                # 如果使用 Linux / MacOS
                daily["date_str"] = "日期：" + daily["date_obj"].strftime("%Y年%-m月%-d日") + f" ({chinese_weekday})"
            except ValueError:
                # 如果使用 Windows
                daily["date_str"] = "日期：" + daily["date_obj"].strftime("%Y年%m月%d日") + f" ({chinese_weekday})"

        forecast_periods.append(daily)
        
    # 組裝最終的輸出字典
    parsed_weather["location_name"] = city_name
    parsed_weather["county_name"] = city_name
    parsed_weather["forecast_periods"] = forecast_periods

    # 記錄並回傳結果
    """
    在返回結果之前，將解析後的數據轉換為 JSON 字串並記錄下來，用於偵錯。
    由於 `datetime.date` 物件不能直接被 `json.dumps` 序列化，這裡使用 `default=str` 參數來將它轉換為字串。
    確保日誌輸出的完整性和可讀性，同時也對可能發生的序列化錯誤進行處理，避免因為日誌記錄失敗而影響主程式的運作。
    """
    try:
        parsed_weather_for_log = json.loads(json.dumps(parsed_weather, default=str))
        logger.debug(f"✅ 預報解析結果: {json.dumps(parsed_weather_for_log, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"解析結果序列化到日誌時出錯: {e}")
        logger.debug(f"✅ 預報解析結果 (簡化): 總數 {len(forecast_periods)} 個時段。")
    
    logger.info(f"解析完成: {city_name} 共 {len(forecast_periods)} 個時段天氣資料。")
    return parsed_weather