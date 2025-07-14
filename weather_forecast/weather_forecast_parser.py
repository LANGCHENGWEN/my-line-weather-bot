# weather_forecast_parser.py
# 專門解析天氣預報數據
import logging
import datetime # 導入 datetime 模組

logger = logging.getLogger(__name__)

def parse_forecast_weather(cwa_data: dict, township_name: str) -> dict:
    """
    解析中央氣象署「鄉鎮未來一週天氣預報」(F-D0047-091) 資料。
    回傳一個字典，包含指定鄉鎮市區的多個預報時段資訊。
    通常 F-D0047-091 會提供未來 7 天的「每日」或「每 12 小時」預報。

    Args:
        cwa_data (dict): 原始的 CWA API 回應數據 (來自 F-D0047-091)。
        township_name (str): 要查詢的鄉鎮市區名稱。
    Returns:
        dict: 包含解析後天氣資訊的字典，或空字典。
              範例結構：
              {
                  'location_name': '北區',
                  'county_name': '臺中市',
                  'forecast_periods': [
                      {'date': 'YYYY-MM-DD', 'period_name': '今晚明晨', 'Wx': '...', 'MinT': '...', 'MaxT': '...', 'PoP': '...'},
                      ...
                  ]
              }
    """
    parsed_weather = {}
    try:
        # F-D0047-091 的 records 下是 locations
        locations_list = cwa_data.get('records', {}).get('Locations', [])
        if not locations_list:
            logger.error("CWA API 資料中缺少 'records.Locations' 或其為空。")
            return {}
        
        # F-D0047-091 的 Locations 列表通常只有一個元素，代表一個大區域 (如 '台灣')
        # 然後這個元素裡面才會有 'Location' 列表，包含各縣市
        county_or_area_data = locations_list[0] if locations_list else None
        if not county_or_area_data:
            logger.error("CWA API 資料中缺少縣市/區域資料。")
            return {}
        
        # 從 LocationsName 取得大區域名稱 (例如 '台灣')
        # 你的範例 JSON 顯示 LocationsName 是 '台灣'
        area_name = county_or_area_data.get('LocationsName', '未知區域') 

        # 在 county_or_area_data.Location (大寫 L) 中找到對應的 township (這裡是縣市層級)
        target_location_data = None
        for loc in county_or_area_data.get('Location', []):
            if loc.get('LocationName') == township_name:
                target_location_data = loc
                break

        if not target_location_data:
            logger.warning(f"在預報數據中找不到 '{township_name}' 的資料。請確認輸入的是縣市名稱，例如:「 台中市 」。")
            return {}
        
        # 實際的縣市名稱應該從 target_location_data 中獲取，通常就是 township_name 本身
        # 因為 F-D0047-091 是直接提供縣市為單位
        county_name = target_location_data.get('LocationsName', '未知縣市') # F-D0047-091 用 LocationsName
        
        logger.debug(f"正在解析縣市 '{county_name}', 鄉鎮市區 (這裡指縣市) '{township_name}' 的數據。")
        
        # 創建一個字典，以 'startTime' 作為鍵來匯總所有氣象元素
        # F-D0047-091 通常有分日/夜，或 3/6 小時時段，每個元素有自己的 time 陣列
        # 我們需要統一按時間點來聚合數據
        aggregated_forecast = {}

        for element in target_location_data.get('WeatherElement', []):
            element_name = element.get('ElementName')
            if not element_name:
                continue

            for time_entry in element.get('Time', []):
                start_time_str = time_entry.get('StartTime')
                end_time_str = time_entry.get('EndTime')

                if not start_time_str or not end_time_str:
                    logger.warning(f"時間數據不完整，跳過此項: StartTime={start_time_str}, EndTime={end_time_str}")
                    continue

                # 初始化該時間段的數據
                if start_time_str not in aggregated_forecast:
                    aggregated_forecast[start_time_str] = {
                        'start_time': start_time_str,
                        'end_time': end_time_str
                    }

                # 根據ElementName提取數據，數據在 ElementValue 列表中
                element_values = time_entry.get('ElementValue', [])
                if not element_values:
                    # logger.warning(f"元素 '{element_name}' 在時段 {start_time_str} 缺少 ElementValue。")
                    continue

                # 提取 ElementValue 中的實際值
                # 這裡需要根據 ElementName 來決定提取哪個鍵
                value_dict = element_values[0] # 通常 ElementValue 只有一個字典

                # 根據 elementName 和 parameter.parameterName/Value 提取數據
                if element_name == 'WeatherDescription': # 天氣現象描述
                    aggregated_forecast[start_time_str]['weather_desc'] = value_dict.get('WeatherDescription', 'N/A')
                elif element_name == '最高溫度': # 最高溫度
                    aggregated_forecast[start_time_str]['max_temp'] = value_dict.get('MaxTemperature', 'N/A')
                elif element_name == '最高體感溫度': # 最高體感溫度
                    aggregated_forecast[start_time_str]['max_feel'] = value_dict.get('MaxApparentTemperature', 'N/A')
                elif element_name == '最低溫度': # 最低溫度
                    aggregated_forecast[start_time_str]['min_temp'] = value_dict.get('MinTemperature', 'N/A')
                elif element_name == '最低體感溫度': # 最低體感溫度
                    aggregated_forecast[start_time_str]['min_feel'] = value_dict.get('MinApparentTemperature', 'N/A')
                elif element_name == '平均相對濕度': # 濕度
                    aggregated_forecast[start_time_str]['humidity'] = value_dict.get('RelativeHumidity', 'N/A')
                elif element_name == 'ProbabilityOfPrecipitation': # 降雨機率
                    aggregated_forecast[start_time_str]['pop'] = value_dict.get('ProbabilityOfPrecipitation', 'N/A')
                elif element_name == 'WindSpeed': # 風速
                    aggregated_forecast[start_time_str]['wind_speed'] = value_dict.get('WindSpeed', 'N/A')
                elif element_name == 'WindDirection': # 風向
                    aggregated_forecast[start_time_str]['wind_dir'] = value_dict.get('WindDirection', 'N/A')
                elif element_name == 'MaxComfortIndexDescription': # 最大舒適度指數描述
                    aggregated_forecast[start_time_str]['comfort_max'] = value_dict.get('MaxComfortIndexDescription', 'N/A')
                elif element_name == 'MinComfortIndexDescription': # 最小舒適度指數描述
                    aggregated_forecast[start_time_str]['comfort_min'] = value_dict.get('MinComfortIndexDescription', 'N/A')
                elif element_name == 'UVIndex': # 紫外線指數
                    aggregated_forecast[start_time_str]['uv_index'] = value_dict.get('UVIndex', 'N/A')
                # 您可以根據實際資料集，繼續添加其他元素

        # 將聚合的數據轉換為排序的列表
        forecast_periods = []
        for start_time in sorted(aggregated_forecast.keys()):
            period_data = aggregated_forecast[start_time]

            # 格式化日期和時段
            try:
                start_dt = datetime.datetime.fromisoformat(period_data['start_time'])
                end_dt = datetime.datetime.fromisoformat(period_data['end_time'])

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

                period_data['date'] = date_prefix # 加入日期前綴
                period_data['period_name'] = period_name

            except (ValueError, TypeError) as ve:
                logger.error(f"時間格式解析錯誤: {ve}。原始時間字串: {period_data.get('start_time')}, {period_data.get('end_time')}")
                period_data['date'] = "N/A"
                period_data['period_name'] = "N/A"

            forecast_periods.append(period_data)
        
        parsed_weather['location_name'] = township_name
        parsed_weather['county_name'] = county_name
        parsed_weather['forecast_periods'] = forecast_periods
        logger.info(f"已解析 {county_name}{township_name} 的天氣預報資料 (F-D0047-091)。共 {len(forecast_periods)} 個時段。")

    except Exception as e:
        logger.error(f"解析預報天氣資料時發生錯誤: {e}", exc_info=True)
        return {}
    
    return parsed_weather