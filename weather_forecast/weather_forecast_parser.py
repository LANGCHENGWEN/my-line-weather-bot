# weather_forecast_parser.py
# 專門解析天氣預報數據
import json
import logging
import datetime # 導入 datetime 模組

logger = logging.getLogger(__name__)

def safe_val(val):
    return "N/A" if val in [None, "-", ""] else val

# 每個欄位對應的 Key
element_field_map = {
    "天氣現象": ("weather_desc", "Weather"),
    "最高溫度": ("max_temp", "MaxTemperature"),
    "最高體感溫度": ("max_feel", "MaxApparentTemperature"),
    "最低溫度": ("min_temp", "MinTemperature"),
    "最低體感溫度": ("min_feel", "MinApparentTemperature"),
    "平均相對濕度": ("humidity", "RelativeHumidity"),
    "12小時降雨機率": ("pop", "ProbabilityOfPrecipitation"),
    "風速": ("wind_speed", "WindSpeed"),
    "風向": ("wind_dir", "WindDirection"),
    "最大舒適度指數": ("comfort_max", "MaxComfortIndexDescription"),
    "最小舒適度指數": ("comfort_min", "MinComfortIndexDescription"),
    "紫外線指數": ("uv_index", "UVIndex")
}

def parse_forecast_weather(cwa_data: dict, county_name: str) -> dict:
    """
    解析中央氣象署「F-D0047-091」資料 (未來一週逐12小時天氣預報)。
    
    Args:
        cwa_data (dict): 原始 API 回傳 JSON。
        county_name (str): 要查詢的縣市名稱，例如 "臺中市"。

    Returns:
        dict: 解析後的天氣資料結構，含多個時間段的預報。
    """
    logger.debug(f"實際取得的 CWA JSON 結構: {json.dumps(cwa_data, indent=2, ensure_ascii=False)}")
    
    parsed_weather = {}

    # 先取到 records 列表
    records = cwa_data.get("records", {})
    if not records:
        logger.error("CWA API 資料中缺少 'records' 或其為空。")
        return {}
    
    # F-D0047-091 的 records 下是 locations
    locations = records.get("Locations", [])
    if not locations:
        logger.error("CWA API 資料中缺少 'Locations' 或其為空。")
        return {}
    
    # 在 location 裡找 township_name (注意小寫)
    all_locations = locations[0].get("Location", [])
    if not all_locations:
        logger.error("Locations 中缺少 'Location'。")
        return {}

    # 列出所有 LocationName，方便 debug
    location_names = [loc.get("LocationName") for loc in all_locations]
    logger.info(f"可用 LocationName 清單: {location_names}")

    target_location = None
    for loc in all_locations:
        if loc.get("LocationName") == county_name:
            target_location = loc
            break

    if not target_location:
        logger.warning(f"找不到指定縣市 '{county_name}' 的資料。")
        return {}
    
    logger.info(f"✅ 成功找到縣市 {county_name} 的資料")
    logger.info(f"共取得 {len(target_location['WeatherElement'])} 個氣象元素")
    for el in target_location["WeatherElement"]:
        logger.info(f"元素 {el['ElementName']} 有 {len(el['Time'])} 筆時間段")
    
    # ✅ 在這裡加上這一行，檢查這個地點下所有欄位
    logger.debug(f"📦 target_location: {json.dumps(target_location, ensure_ascii=False, indent=2)}")
    
    for element in target_location.get("WeatherElement", []):
        logger.info(f"➡️ 目前 ElementName：{element.get('ElementName')}")
    
    # 聚合時間段資料
    aggregated_forecast = {}

    for element in target_location.get("WeatherElement", []):
        element_name = element.get("ElementName")
        logger.info(f"➡️ 目前 ElementName：{element_name}")
        logger.debug(f"{element_name} 的 Time 資料: {json.dumps(element.get('Time', []), ensure_ascii=False, indent=2)}")
        if element_name not in element_field_map:
            continue

        target_key, inner_field = element_field_map[element_name]

        for time_entry in element.get("Time", []):
            start_time = time_entry.get("StartTime")
            end_time = time_entry.get("EndTime")

            if not start_time or not end_time:
                logger.warning(f"時間資訊不完整: {start_time}, {end_time}")
                continue

            # ✅ 改用時間段當 key，避免欄位資料無法聚合
            time_key = f"{start_time}_{end_time}"

            # 初始化該時間段的數據
            if time_key not in aggregated_forecast:
                aggregated_forecast[time_key] = {
                    "start_time": start_time,
                    "end_time": end_time
                }

            # 提取 ElementValue 中的實際值
            # 這裡需要根據 ElementName 來決定提取哪個鍵
            value_dict = time_entry.get("ElementValue", [{}])[0] # 通常 ElementValue 只有一個字典
            val = safe_val(value_dict.get(inner_field))
            aggregated_forecast[time_key][target_key] = val
            logger.debug(f"🧪 [{element_name}] 解析元素: start={start_time}, end={end_time}, key={inner_field}, val={val}, 原始 value_dict={value_dict}")
            logger.debug(f"時間 {start_time} 元素 {element_name} 的 value_dict keys: {list(value_dict.keys())} / value_dict content: {value_dict}")

            """
            # 根據 elementName 和 parameter.parameterName/Value 提取數據
            if element_name == "天氣現象": # 天氣現象描述
                aggregated_forecast[start_time]["weather_desc"] = safe_val(value_dict.get("Weather", "N/A"))
            elif element_name == "最高溫度": # 最高溫度
                aggregated_forecast[start_time]["max_temp"] = safe_val(value_dict.get("MaxTemperature", "N/A"))
            elif element_name == "最高體感溫度": # 最高體感溫度
                aggregated_forecast[start_time]["max_feel"] = safe_val(value_dict.get("MaxApparentTemperature", "N/A"))
            elif element_name == "最低溫度": # 最低溫度
                aggregated_forecast[start_time]["min_temp"] = safe_val(value_dict.get("MinTemperature", "N/A"))
            elif element_name == "最低體感溫度": # 最低體感溫度
                aggregated_forecast[start_time]["min_feel"] = safe_val(value_dict.get("MinApparentTemperature", "N/A"))
            elif element_name == "平均相對濕度": # 濕度
                aggregated_forecast[start_time]["humidity"] = safe_val(value_dict.get("RelativeHumidity", "N/A"))
            elif element_name == "12小時降雨機率": # 降雨機率
                aggregated_forecast[start_time]["pop"] = safe_val(value_dict.get("ProbabilityOfPrecipitation", "N/A"))
            elif element_name == "風速": # 風速
                aggregated_forecast[start_time]["wind_speed"] = safe_val(value_dict.get("WindSpeed", "N/A"))
            elif element_name == "風向": # 風向
                aggregated_forecast[start_time]["wind_dir"] = safe_val(value_dict.get("WindDirection", "N/A"))
            elif element_name == "最大舒適度指數": # 最大舒適度指數描述
                aggregated_forecast[start_time]["comfort_max"] = safe_val(value_dict.get("MaxComfortIndexDescription", "N/A"))
            elif element_name == "最小舒適度指數": # 最小舒適度指數描述
                aggregated_forecast[start_time]["comfort_min"] = safe_val(value_dict.get("MinComfortIndexDescription", "N/A"))
            elif element_name == "紫外線指數": # 紫外線指數
                aggregated_forecast[start_time]["uv_index"] = safe_val(value_dict.get("UVIndex", "N/A"))
            # 您可以根據實際資料集，繼續添加其他元素
            """

    # 將聚合的數據轉換為排序的列表
    forecast_periods = []
    for time_key in sorted(aggregated_forecast.keys()):
        period = aggregated_forecast[time_key]

        # 格式化日期和時段
        try:
            start_dt = datetime.datetime.fromisoformat(period["start_time"])
            end_dt = datetime.datetime.fromisoformat(period["end_time"])

            # 判斷時段是「今天」、「明天」或其他日期
            current_date = datetime.datetime.now(start_dt.tzinfo).date() # 確保時區一致
            forecast_date = start_dt.date()

            if forecast_date == current_date:
                date_prefix = "今天"
            elif forecast_date == current_date + datetime.timedelta(days=1):
                date_prefix = "明天"
            else:
                date_prefix = forecast_date.strftime("%m/%d") # 例如 07/03

            # 判斷時段是白天 (06-18) 還是夜晚 (18-06)
            if 6 <= start_dt.hour < 18 and 6 <= end_dt.hour <= 18:
                period_name = "白天"
            elif (18 <= start_dt.hour <= 23 or 0 <= start_dt.hour < 6) and \
                    (18 <= end_dt.hour <= 23 or 0 <= end_dt.hour < 6):
                period_name = "晚上"
            else:
                # 如果時段橫跨日夜，或者是非標準的12小時制，就顯示時間範圍
                period_name = f"{start_dt.strftime('%H:%M')} ~ {end_dt.strftime('%H:%M')}"

            period['date'] = date_prefix # 加入日期前綴
            period['period_name'] = period_name

            # 格式化完整日期字串
            # 如果你用的是 Linux / MacOS：
            try:
                period['date_str'] = start_dt.strftime("%Y年%-m月%-d日")
            except ValueError:
                # Windows 環境下可用以下格式（不保證所有 Windows Python 版本都支援）
                period['date_str'] = start_dt.strftime("%Y年%m月%d日")

        except (ValueError, TypeError) as ve:
            logger.error(f"時間格式解析錯誤: {ve}。原始時間字串: {period.get('start_time')}, {period.get('end_time')}")
            period['date'] = "N/A"
            period['period_name'] = "N/A"
            period['date_str'] = "N/A"

        forecast_periods.append(period)
        
    parsed_weather['location_name'] = county_name
    parsed_weather['county_name'] = county_name
    parsed_weather['forecast_periods'] = forecast_periods
    
    logger.debug(f"✅ 預報解析結果: {json.dumps(parsed_weather, ensure_ascii=False, indent=2)}")
    logger.info(f"解析完成: {county_name} 共 {len(forecast_periods)} 個時段天氣資料。")
    return parsed_weather