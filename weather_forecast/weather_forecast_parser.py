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

def parse_forecast_weather(cwa_raw_data: dict, city_name: str) -> dict:
    """
    解析中央氣象署「F-D0047-091」資料 (未來一週逐12小時天氣預報)。
    
    Args:
        cwa_data (dict): 原始 API 回傳 JSON。
        county_name (str): 要查詢的縣市名稱，例如 "臺中市"。

    Returns:
        dict: 解析後的天氣資料結構，含多個時間段的預報。
    """
    logger.debug(f"實際取得的 CWA JSON 結構: {json.dumps(cwa_raw_data, indent=2, ensure_ascii=False)}")
    
    parsed_weather = {}

    # 先取到 records 列表
    records = cwa_raw_data.get("records", {})
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
    logger.debug(f"可用 LocationName 清單: {location_names}")

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
    for el in target_location["WeatherElement"]:
        logger.info(f"元素 {el['ElementName']} 有 {len(el['Time'])} 筆時間段")
    
    # ✅ 在這裡加上這一行，檢查這個地點下所有欄位
    logger.debug(f"📦 target_location: {json.dumps(target_location, ensure_ascii=False, indent=2)}")
    
    """
    for element in target_location.get("WeatherElement", []):
        logger.debug(f"➡️ 目前 ElementName：{element.get('ElementName')}")
    """

    # 聚合時間段資料
    daily_aggregated = {}

    for element in target_location.get("WeatherElement", []):
        element_name = element.get("ElementName")
        logger.debug(f"➡️ 目前 ElementName：{element_name}")
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

            start_dt = datetime.datetime.fromisoformat(start_time)
            end_dt = datetime.datetime.fromisoformat(end_time)

            # 依照結束時間 (end_dt) 的日期來決定歸屬哪一天
            date_key = (end_dt - datetime.timedelta(hours=6)).date().isoformat()

            # 判斷 day 或 night
            if start_dt.hour == 6:
                period = "day"
            elif start_dt.hour == 18:
                period = "night"
            else:
                # 萬一遇到特例
                period = "unknown"

            # 初始化該時間段的數據
            if date_key not in daily_aggregated:
                daily_aggregated[date_key] = {
                    "date": date_key,
                    "start_time_day": None,
                    "end_time_day": None,
                    "start_time_night": None,
                    "end_time_night": None
                }

            # 提取 ElementValue 中的實際值
            # 這裡需要根據 ElementName 來決定提取哪個鍵
            value_dict = time_entry.get("ElementValue", [{}])[0] # 通常 ElementValue 只有一個字典
            val = safe_val(value_dict.get(inner_field))

            # 存入正確的 period
            key_name = f"{target_key}_{period}"
            daily_aggregated[date_key][key_name] = val
            logger.debug(f"📅 處理元素: {element_name} / Start: {start_time} / Period: {period} / date_key: {date_key} / inner_field: {inner_field}")
            logger.debug(f"ElementValue: {value_dict} / 取值結果: {val}")

            # 記錄原始時間
            if period == "day":
                daily_aggregated[date_key]["start_time_day"] = start_time
                daily_aggregated[date_key]["end_time_day"] = end_time
            else:
                daily_aggregated[date_key]["start_time_night"] = start_time
                daily_aggregated[date_key]["end_time_night"] = end_time

    # 將聚合的數據轉換為排序的列表
    forecast_periods = []
    for date_key in sorted(daily_aggregated.keys()):
        daily = daily_aggregated[date_key]

        # 格式化日期和時段
        try:
            date_obj = datetime.date.fromisoformat(daily["date"])
            current_date = datetime.datetime.now().date() # 確保時區一致

            # 判斷時段是「今天」、「明天」或其他日期
            if date_obj == current_date:
                date_prefix = "今天"
            elif date_obj == current_date + datetime.timedelta(days=1):
                date_prefix = "明天"
            else:
                date_prefix = date_obj.strftime("%m/%d") # 例如 07/03

            daily["date_prefix"] = date_prefix # 加入日期前綴

            # 格式化完整日期字串
            # 如果你用的是 Linux / MacOS：
            try:
                daily["date_str"] = date_obj.strftime("%Y年%-m月%-d日")
            except ValueError:
                # Windows 環境下可用以下格式（不保證所有 Windows Python 版本都支援）
                daily["date_str"] = date_obj.strftime("%Y年%m月%d日")

        except (ValueError, TypeError) as ve:
            logger.error(f"時間格式解析錯誤: {ve}。原始時間字串: {daily.get('start_time_day')}, {daily.get('end_time_day')}")
            daily["date_prefix"] = "N/A"
            daily["date_str"] = "N/A"

        forecast_periods.append(daily)
        
    parsed_weather["location_name"] = city_name
    parsed_weather["county_name"] = city_name
    parsed_weather["forecast_periods"] = forecast_periods
    
    logger.debug(f"✅ 預報解析結果: {json.dumps(parsed_weather, ensure_ascii=False, indent=2)}")
    logger.info(f"解析完成: {city_name} 共 {len(forecast_periods)} 個時段天氣資料。")
    return parsed_weather