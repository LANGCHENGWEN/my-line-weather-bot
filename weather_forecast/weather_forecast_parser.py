# weather_forecast_parser.py
# 專門解析天氣預報數據
import json
import logging
import datetime # 導入 datetime 模組

logger = logging.getLogger(__name__)

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
        
    # Locations 通常只有一筆，是整個台灣
    taiwan_data = locations[0]
    # 在 location 裡找 township_name (注意小寫)
    all_locations = taiwan_data.get("Location", [])
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
    
    # 聚合時間段資料
    aggregated_forecast = {}

    for element in target_location.get("WeatherElement", []):
        element_name = element.get("ElementName")
        if not element_name:
            continue

        for time_entry in element.get("Time", []):
            start_time = time_entry.get("StartTime")
            end_time = time_entry.get("EndTime")

            if not start_time or not end_time:
                logger.warning(f"時間資訊不完整: {start_time}, {end_time}")
                continue

            # 初始化該時間段的數據
            if start_time not in aggregated_forecast:
                aggregated_forecast[start_time] = {
                    "start_time": start_time,
                    "end_time": end_time
                }

            # 根據ElementName提取數據，數據在 ElementValue 列表中
            element_values = time_entry.get("ElementValue", [])
            if not element_values:
                # logger.warning(f"元素 '{element_name}' 在時段 {start_time_str} 缺少 ElementValue。")
                continue

            # 提取 ElementValue 中的實際值
            # 這裡需要根據 ElementName 來決定提取哪個鍵
            value_dict = element_values[0] # 通常 ElementValue 只有一個字典

            # 根據 elementName 和 parameter.parameterName/Value 提取數據
            if element_name == "WeatherDescription": # 天氣現象描述
                aggregated_forecast[start_time]["weather_desc"] = value_dict.get("WeatherDescription", "N/A")
            elif element_name == "最高溫度": # 最高溫度
                aggregated_forecast[start_time]["max_temp"] = value_dict.get("MaxTemperature", "N/A")
            elif element_name == "最高體感溫度": # 最高體感溫度
                aggregated_forecast[start_time]["max_feel"] = value_dict.get("MaxApparentTemperature", "N/A")
            elif element_name == "最低溫度": # 最低溫度
                aggregated_forecast[start_time]["min_temp"] = value_dict.get("MinTemperature", "N/A")
            elif element_name == "最低體感溫度": # 最低體感溫度
                aggregated_forecast[start_time]["min_feel"] = value_dict.get("MinApparentTemperature", "N/A")
            elif element_name == "平均相對濕度": # 濕度
                aggregated_forecast[start_time]["humidity"] = value_dict.get("RelativeHumidity", "N/A")
            elif element_name == "ProbabilityOfPrecipitation": # 降雨機率
                aggregated_forecast[start_time]["pop"] = value_dict.get("ProbabilityOfPrecipitation", "N/A")
            elif element_name == "WindSpeed": # 風速
                aggregated_forecast[start_time]["wind_speed"] = value_dict.get("WindSpeed", "N/A")
            elif element_name == "WindDirection": # 風向
                aggregated_forecast[start_time]["wind_dir"] = value_dict.get("WindDirection", "N/A")
            elif element_name == "MaxComfortIndexDescription": # 最大舒適度指數描述
                aggregated_forecast[start_time]["comfort_max"] = value_dict.get("MaxComfortIndexDescription", "N/A")
            elif element_name == "MinComfortIndexDescription": # 最小舒適度指數描述
                aggregated_forecast[start_time]["comfort_min"] = value_dict.get("MinComfortIndexDescription", "N/A")
            elif element_name == "UVIndex": # 紫外線指數
                aggregated_forecast[start_time]["uv_index"] = value_dict.get("UVIndex", "N/A")
            # 您可以根據實際資料集，繼續添加其他元素

        # 將聚合的數據轉換為排序的列表
        forecast_periods = []
        for start_time in sorted(aggregated_forecast.keys()):
            period = aggregated_forecast[start_time]

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

            except (ValueError, TypeError) as ve:
                logger.error(f"時間格式解析錯誤: {ve}。原始時間字串: {period.get('start_time')}, {period.get('end_time')}")
                period['date'] = "N/A"
                period['period_name'] = "N/A"

            forecast_periods.append(period)
        
        parsed_weather['location_name'] = county_name
        parsed_weather['county_name'] = county_name
        parsed_weather['forecast_periods'] = forecast_periods
        
        logger.info(f"解析完成: {county_name} 共 {len(forecast_periods)} 個時段天氣資料。")
        return parsed_weather