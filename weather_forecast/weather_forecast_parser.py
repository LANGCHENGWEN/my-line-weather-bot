# weather_forecast/weather_forecast_parser.py
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

def is_weekend(date_obj: datetime.date) -> bool:
    """判斷給定的日期是否為週末 (週六或週日)。"""
    return date_obj.weekday() >= 5  # 5 是週六, 6 是週日

# 新增輔助函數來判斷日期前綴
def get_date_prefix(date_obj: datetime.date) -> str:
    current_date = datetime.datetime.now().date()
    if date_obj == current_date:
        return "今天"
    elif date_obj == current_date + datetime.timedelta(days=1):
        return "明天"
    else:
        return date_obj.strftime("%m/%d") # 例如 07/03

def parse_forecast_weather(cwa_raw_data: dict, city_name: str) -> dict:
    """
    解析中央氣象署「F-D0047-091」資料 (未來一週逐12小時天氣預報)。
    
    Args:
        cwa_data (dict): 原始 API 回傳 JSON。
        county_name (str): 要查詢的縣市名稱，例如 "臺中市"。

    Returns:
        dict: 解析後的天氣資料結構，含多個時間段的預報。
    """
    logger.debug(f"進入 parse_forecast_weather 函數，正在處理地點: {city_name}")

    # 確保你傳入的 cwa_raw_data 是一個字典
    if not isinstance(cwa_raw_data, dict):
        logger.error(f"cwa_raw_data 不是有效的字典類型: {type(cwa_raw_data)}")
        return {"location_name": city_name, "forecast_periods": []}

    logger.debug(f"實際取得的 CWA JSON 結構: {json.dumps(cwa_raw_data, indent=2, ensure_ascii=False)[:2000]}...")
    
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
    logger.debug(f"📦 target_location 內容: {json.dumps(target_location, ensure_ascii=False, indent=2)}")

    for el in target_location["WeatherElement"]:
        logger.info(f"元素 {el['ElementName']} 有 {len(el['Time'])} 筆時間段")
    
    # ✅ 在這裡加上這一行，檢查這個地點下所有欄位
    # logger.debug(f"📦 target_location: {json.dumps(target_location, ensure_ascii=False, indent=2)}")
    
    """
    for element in target_location.get("WeatherElement", []):
        logger.debug(f"➡️ 目前 ElementName：{element.get('ElementName')}")
    """

    # 聚合時間段資料
    daily_aggregated = {}

    for element in target_location.get("WeatherElement", []):
        element_name = element.get("ElementName")
        logger.debug(f"➡️ 目前 ElementName：{element_name}")
        # logger.debug(f"{element_name} 的 Time 資料: {json.dumps(element.get('Time', []), ensure_ascii=False, indent=2)}")
        if element_name not in element_field_map:
            logger.debug(f"ElementName: {element_name} 不在 element_field_map 中。跳過。")
            continue

        target_key, inner_field = element_field_map[element_name]
        logger.debug(f"ElementName: {element_name}, 對應輸出鍵: {target_key}, 內部取值鍵: {inner_field}")

        times_data = element.get("Time", [])
        if not times_data:
            logger.debug(f"ElementName: {element_name} 沒有 Time 數據。跳過。")
            continue

        for time_entry in element.get("Time", []):
            start_time = time_entry.get("StartTime")
            end_time = time_entry.get("EndTime")

            if not start_time or not end_time:
                logger.warning(f"時間資訊不完整，跳過該筆 time_entry: {time_entry}")
                continue

            try:
                start_dt = datetime.datetime.fromisoformat(start_time)
                # end_dt = datetime.datetime.fromisoformat(end_time)

                start_dt_no_tz = start_dt.replace(tzinfo=None)
                # end_dt_no_tz = end_dt.replace(tzinfo=None) # 對於日期歸屬，最好用結束時間
            except ValueError as e:
                logger.error(f"解析時間字串失敗: {start_time} 或 {end_time}. 錯誤: {e}")
                continue

            # 依照結束時間 (end_dt) 的日期來決定歸屬哪一天
            # CWA 12小時預報慣例：06-18點屬於當天白天，18-06點跨日，結束時間的日期是隔天
            # 因此，對於結束時間在 06:00 (隔天) 的時段，我們應該將其歸屬到「前一天」的夜晚。
            # 簡單的判斷方式是，如果結束時間的小時數 <= 6 點，則日期為前一天。
            """
            if end_dt_no_tz.hour <= 6: # 如果結束時間是隔天 06:00
                 date_key = (end_dt_no_tz - datetime.timedelta(days=1)).date().isoformat()
            else: # 如果結束時間是當天 18:00
                 date_key = end_dt_no_tz.date().isoformat()

            # 依照結束時間 (end_dt) 的日期來決定歸屬哪一天
            date_key = (end_dt - datetime.timedelta(hours=6)).date().isoformat()
            """

            # 判斷 day 或 night
            # 如果起始時間是 06:00 或 12:00，通常屬於白天時段 (到 18:00)
            period = "unknown"
            if start_dt_no_tz.hour >= 6 and start_dt_no_tz.hour < 18: # 06:00 ~ 17:59:59 的時段為白天
                period = "day"
            # 如果起始時間是 18:00 或 00:00 (通常指前一天午夜到隔天上午)，通常屬於夜晚時段
                # 白天時段的日期就是其 StartTime 的日期
                date_key = start_dt_no_tz.date().isoformat()
            elif start_dt_no_tz.hour >= 18 or start_dt_no_tz.hour < 6: # 18:00 ~ 隔日 05:59:59 的時段為夜晚
                period = "night"
                date_key = start_dt_no_tz.date().isoformat()
            else:
                # 萬一遇到特例
                logger.warning(f"無法判斷時段屬於白天或夜晚，StartTime: {start_time}. 歸類為 unknown.")
                date_key = start_dt_no_tz.date().isoformat() # 即使未知也給個日期

            # 初始化該時間段的數據
            if date_key not in daily_aggregated:
                daily_aggregated[date_key] = {
                    "date": date_key,
                    "is_weekend": is_weekend(datetime.date.fromisoformat(date_key)),
                    "date_prefix": get_date_prefix(datetime.date.fromisoformat(date_key)),
                    "date_str": "",
                    "date_obj": datetime.date.fromisoformat(date_key), # 保存 date_obj
                    "start_time_day": None,
                    "end_time_day": None,
                    "start_time_night": None,
                    "end_time_night": None
                }
                logger.debug(f"新增日期 {date_key}，是否週末: {daily_aggregated[date_key]['is_weekend']}")

            # 提取 ElementValue 中的實際值
            # 這裡需要根據 ElementName 來決定提取哪個鍵
            value_dict = time_entry.get("ElementValue", [{}])[0] # 通常 ElementValue 只有一個字典
            val = safe_val(value_dict.get(inner_field))

            logger.debug(f"📅 處理元素: {element_name} / Start: {start_time} / End: {end_time} / Period: {period} / date_key: {date_key} / inner_field: {inner_field}")
            logger.debug(f"ElementValue: {value_dict} / 取值結果: {val}")

            daily_aggregated[date_key][f"{target_key}_{period}"] = val

            """
            # 存入正確的 period
            # 確保該日期的該時段字典存在
            if period not in daily_aggregated[date_key]:
                daily_aggregated[date_key][period] = {}

            # 將數值存入正確的 key 中 (例如 max_temp_day)
            daily_aggregated[date_key][f"{target_key}_{period}"] = val
            """

            # 存入正確的 period
            # key_name = f"{target_key}_{period}"
            # daily_aggregated[date_key][key_name] = val
            # logger.debug(f"📅 處理元素: {element_name} / Start: {start_time} / Period: {period} / date_key: {date_key} / inner_field: {inner_field}")
            # logger.debug(f"ElementValue: {value_dict} / 取值結果: {val}")

            # 記錄原始時間字串，用於後續填充 Flex Message
            if period == "day":
                daily_aggregated[date_key]["start_time_day"] = start_time
                daily_aggregated[date_key]["end_time_day"] = end_time
            elif period == "night":
                daily_aggregated[date_key]["start_time_night"] = start_time
                daily_aggregated[date_key]["end_time_night"] = end_time
            else: # for "unknown" periods, we might still want to capture times if they appear
                 logger.warning(f"未知時段的 StartTime/EndTime: {start_time} / {end_time}")

    # 將聚合的數據轉換為排序的列表
    forecast_periods = []

    for date_key in sorted(daily_aggregated.keys()):
        daily = daily_aggregated[date_key]

        if daily["date_obj"]:
            weekday_map_chinese = {
                0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"
            }
            chinese_weekday = weekday_map_chinese.get(daily["date_obj"].weekday(), "")

            # 格式化完整日期字串
            # 如果你用的是 Linux / MacOS：
            try:
                daily["date_str"] = "日期：" + daily["date_obj"].strftime("%Y年%-m月%-d日") + f" ({chinese_weekday})"
            except ValueError:
                # Windows 環境下可用以下格式（不保證所有 Windows Python 版本都支援）
                daily["date_str"] = "日期：" + daily["date_obj"].strftime("%Y年%m月%d日") + f" ({chinese_weekday})"

        forecast_periods.append(daily)
        
    parsed_weather["location_name"] = city_name
    parsed_weather["county_name"] = city_name
    parsed_weather["forecast_periods"] = forecast_periods

    # *** 這是新的修正點：在進行 json.dumps 之前，移除所有 date_obj ***
    # 創建一個深拷貝，避免修改原始數據影響後續處理
    try:
        parsed_weather_for_log = json.loads(json.dumps(parsed_weather, default=str)) # 使用 default=str 處理無法序列化的物件
        logger.debug(f"✅ 預報解析結果: {json.dumps(parsed_weather_for_log, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"解析結果序列化到日誌時出錯: {e}")
        logger.debug(f"✅ 預報解析結果 (簡化): 總數 {len(forecast_periods)} 個時段。") # 如果失敗，只輸出簡化訊息
    
    logger.info(f"解析完成: {city_name} 共 {len(forecast_periods)} 個時段天氣資料。")
    return parsed_weather