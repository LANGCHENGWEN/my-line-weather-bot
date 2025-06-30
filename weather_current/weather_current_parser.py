# weather_current_parser.py
# 專門解析即時天氣數據(天氣觀測報告-有人氣象站資料 (O-A0003-001))
import logging
from datetime import datetime
from config import setup_logging

logger = setup_logging(__name__)

def calculate_apparent_temperature(temp_c: float, humidity_percent: float) -> float | str:
    """
    簡化版的體感溫度計算。這是一個基於熱指數的近似值，非精確科學公式。
    來源參考：https://en.wikipedia.org/wiki/Heat_index
    """
    if not isinstance(temp_c, (int, float)) or not isinstance(humidity_percent, (int, float)):
        return "N/A"

    # 將濕度從百分比轉換為小數
    humidity = humidity_percent / 100.0

    # 將攝氏度轉換為華氏度 (Heat Index 公式常用華氏度)
    temp_f = (temp_c * 9/5) + 32

    # 這是美國國家氣象局的熱指數公式簡化版本 (通常適用於華氏 80 度以上)
    # 如果溫度較低，直接返回實際溫度或進行風寒計算
    # 低溫時體感溫度通常等於實際溫度，或應考慮風寒
    if temp_f < 80: # 在較低溫時，熱指數意義不大，直接返回實際溫度
        return round(temp_c, 1)
    
    # Heat Index Formula (Simplified for demonstration)
    # 使用 round() 確保計算結果的浮點精度
    apparent_temp_f = -42.379 + 2.04901523*temp_f + 10.14333127*humidity - 0.22475541*temp_f*humidity - 6.83783e-3*temp_f**2 - 5.481717e-2*humidity**2 + 1.22874e-3*temp_f**2*humidity + 8.5282e-4*temp_f*humidity**2 - 1.99e-6*temp_f**2*humidity**2

    # 將華氏度轉換回攝氏度
    apparent_temp_c = (apparent_temp_f - 32) * 5/9

    # 如果計算結果與實際溫度差異不大，就直接返回實際溫度
    if abs(apparent_temp_c - temp_c) < 1.0: # 如果差異小於1度，就用實際溫度
        return round(temp_c, 1)

    return round(apparent_temp_c, 1)

def get_wind_direction_description(degrees: float | str) -> str:
    """
    將風向角度轉換為中文描述。
    """
    
    if not isinstance(degrees, (int, float)):
        return "N/A"

    directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]
    

def parse_current_weather(cwa_data: dict, query_location_name: str) -> dict | None: # 修改返回類型提示
    """
    解析中央氣象署 O-A0003-001 (有人氣象站資料) 的原始 JSON 數據，
    提取出主要的天氣資訊。
    
    Args:
        cwa_data (dict): 從 CWA API 獲取的原始 JSON 數據。
        query_location_name (str): 用戶查詢的地點名稱，用於匹配資料。
        
    Returns:
        dict: 包含解析並完全格式化後天氣數據的字典，如果找不到數據則為 None。
              這個字典的鍵值對可以直接用於 Flex Message 填充。
    """
    # 檢查數據基本結構和成功標誌
    if not cwa_data or cwa_data.get('success') != 'true' or \
       'records' not in cwa_data or 'Station' not in cwa_data['records']:
        logger.warning("即時觀測數據格式不正確或缺少關鍵鍵，無法解析。")
        return None # 解析失敗返回 None
    
    target_station_data = None

    # 遍歷所有測站，尋找匹配的地點
    # 注意：query_location_name 應該與 CWA API 返回的 StationName 精確匹配
    for station in cwa_data['records']['Station']:
        # 使用 StationName 進行匹配。
        # 注意：CWA API 的 StationName 可能不完全等於 LOCATION_NAME
        # 在實際應用中，您可能需要一個觀測站名稱與使用者查詢地點的映射表。
        # 這裡假設 location_name 就是 CWA 的 StationName。
        if station.get('StationName') == query_location_name:
            target_station_data = station
            break

    # 如果找不到精確匹配，則嘗試使用第一個測站的數據作為 fallback (可選，但為了範例運行性保留)
    if not target_station_data and cwa_data['records']['Station']:
        target_station_data = cwa_data['records']['Station'][0]
        logger.warning(f"未找到精確匹配地點 '{query_location_name}' 的觀測站，將使用第一個觀測站 '{target_station_data.get('StationName', '未知')}' 的數據。")

    if not target_station_data:
        logger.warning(f"在即時觀測數據中找不到 '{query_location_name}' 或任何測站的資料。")
        return None # 返回 None 表示無法解析
    
    # 提取原始天氣元素
    obs_time_str = target_station_data.get('ObsTime', {}).get('DateTime')
    weather_elements = target_station_data.get('WeatherElement', {})
    
    # 初始化一個字典來存放所有解析和**最終格式化**後的數據
    parsed_and_formatted_info = {}

    # --- 觀測時間處理與格式化 ---
    if obs_time_str and obs_time_str != '-99':
        try:
            # 處理 ISO 8601 格式，確保時區資訊被正確處理
            # .replace('Z', '+00:00') 處理 UTC 時間的 'Z'
            obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00')) 
            parsed_and_formatted_info['observation_time'] = obs_time.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            logger.warning(f"無法解析觀測時間: {obs_time_str}")
            parsed_and_formatted_info['observation_time'] = "N/A" # 解析失敗，設定為 N/A
    else:
        parsed_and_formatted_info['observation_time'] = "N/A"

    # --- 提取、計算並**最終格式化**其他天氣元素 ---
    # 天氣描述 (Weather)
    parsed_and_formatted_info['weather_description'] = weather_elements.get('Weather', 'N/A')

    # 氣溫 (AirTemperature)
    raw_temp_str = weather_elements.get('AirTemperature')
    temp_val = 'N/A'
    if raw_temp_str is not None and raw_temp_str.strip() not in ['', '-99.0', 'N/A'] and raw_temp_str.replace('.', '', 1).isdigit():
        try:
            temp_val = float(raw_temp_str)
            parsed_and_formatted_info['current_temp'] = f"{round(temp_val, 1)}°C"
        except ValueError:
            logger.warning(f"無法將氣溫 '{raw_temp_str}' 轉換為浮點數。")
    
    # 濕度 (RelativeHumidity)
    raw_humidity_str = weather_elements.get('RelativeHumidity')
    hum_val = 'N/A'
    if raw_humidity_str is not None and raw_humidity_str.strip() not in ['', '-99.0', 'N/A'] and raw_humidity_str.isdigit():
        try:
            hum_val = float(raw_humidity_str) # 濕度也可能是浮點數，為了calculate_apparent_temperature
            parsed_and_formatted_info['humidity'] = f"{round(hum_val)}%"
        except ValueError:
            logger.warning(f"無法將濕度 '{raw_humidity_str}' 轉換為數字。")

    # 計算體感溫度並組合到 temp_display
    current_temp_display = f"{round(temp_val, 1)}°C" if temp_val != 'N/A' else 'N/A'
    
    # 初始化 calculated_apparent_temp，以防進入 if 塊之前使用
    calculated_apparent_temp = 'N/A'

    if temp_val != 'N/A' and hum_val != 'N/A':
        calculated_apparent_temp = calculate_apparent_temperature(temp_val, hum_val)

    # 判斷體感溫度是否與實際溫度差異不大，如果差異小於 1 
    # 修改這裡來處理三種情況：顯著差異、相近、N/A
    if isinstance(calculated_apparent_temp, float):
        # 如果體感溫度與實際溫度差異達到 1 度或以上，則顯示體感溫度
        if abs(calculated_apparent_temp - temp_val) >= 1.0: 
            # 顯著差異，顯示具體體感溫度
            parsed_and_formatted_info['sensation_temp_display'] = f"體感: {calculated_apparent_temp}°C"
        else:
            # 差異不顯著，顯示「與實際溫度相近」
            parsed_and_formatted_info['sensation_temp_display'] = "與實際溫度相近"
    else:
        # 無法計算（例如輸入是N/A），顯示 N/A
        parsed_and_formatted_info['sensation_temp_display'] = "N/A"

    parsed_and_formatted_info['current_temp'] = current_temp_display
    # parsed_and_formatted_info['sensation_temp_display'] = f"{calculated_apparent_temp}°C" if isinstance(calculated_apparent_temp, float) and abs(calculated_apparent_temp - temp_val) >= 1.0 else "N/A"
        
    # 濕度 (已在上面處理，這裡只是存儲最終格式化值)
    parsed_and_formatted_info['humidity'] = f"{round(hum_val)}%" if hum_val != 'N/A' else 'N/A'

    # 降水量 (Precipitation)
    raw_precipitation_str = weather_elements.get('Now', {}).get('Precipitation', '-99.0') # <-- 關鍵修正！
    prec_val = float(raw_precipitation_str) if raw_precipitation_str not in ['-99.0', 'N/A'] else 'N/A'
    # parsed_and_formatted_info['precipitation'] = f"{prec_val} mm" if prec_val != 'N/A' else 'N/A'

    # *** 修改這裡：如果為 'N/A'，則顯示 '無' 或 '-' ***
    if prec_val != 'N/A':
        # 判斷是否為 0 降雨，或者顯示具體數值
        # 這裡假設小於 0.1 mm 也算無降雨，可根據需求調整閾值
        # precipitation_data = weather_elements.get('Now', {}).get('Precipitation', '-99.0')
        # prec_val = float(precipitation_data) if precipitation_data not in ['-99.0', 'N/A'] else 'N/A'

        if prec_val <= 0.1: # 幾乎無降雨，顯示 "無"
            parsed_and_formatted_info['precipitation'] = "無"
        else:
            parsed_and_formatted_info['precipitation'] = f"{prec_val} mm"
    else:
        parsed_and_formatted_info['precipitation'] = "無"

    # 風速 (WindSpeed) & 風向 (WindDirection)
    raw_wind_speed_str = weather_elements.get('WindSpeed')
    raw_wind_direction_str = weather_elements.get('WindDirection')
    
    wind_speed_val = 'N/A'
    wind_direction_val = 'N/A'
    wind_direction_desc = 'N/A'

    if raw_wind_speed_str is not None and raw_wind_speed_str.strip() not in ['', '-99.0', 'N/A'] and raw_wind_speed_str.replace('.', '', 1).isdigit():
        try:
            wind_speed_val = float(raw_wind_speed_str)
        except ValueError:
            logger.warning(f"無法將風速 '{raw_wind_speed_str}' 轉換為浮點數。")
    
    if raw_wind_direction_str is not None and raw_wind_direction_str.strip() not in ['', '-99.0', 'N/A'] and raw_wind_direction_str.replace('.', '', 1).isdigit():
        try:
            wind_direction_val = float(raw_wind_direction_str)
            wind_direction_desc = get_wind_direction_description(wind_direction_val)
        except ValueError:
            logger.warning(f"無法將風向 '{raw_wind_direction_str}' 轉換為浮點數。")
    
    # 組合風速和風向
    if wind_speed_val != 'N/A' and wind_direction_desc != 'N/A':
        parsed_and_formatted_info['wind_display'] = f"{wind_speed_val} m/s (風向: {wind_direction_desc})"
    elif wind_speed_val != 'N/A':
        parsed_and_formatted_info['wind_display'] = f"{wind_speed_val} m/s"
    elif wind_direction_desc != 'N/A':
        parsed_and_formatted_info['wind_display'] = f"風向: {wind_direction_desc}"
    else:
        parsed_and_formatted_info['wind_display'] = "無風"

    # 氣壓 (AirPressure)
    raw_pressure_str = weather_elements.get('AirPressure', '-99.0')
    pres_val = float(raw_pressure_str) if raw_pressure_str not in ['-99.0', 'N/A'] else 'N/A'
    parsed_and_formatted_info['pressure'] = f"{pres_val} hPa" if pres_val != 'N/A' else 'N/A'

    # 紫外線指數 (UVI)
    raw_uv_index_str = weather_elements.get('UVIndex', '-99.0')
    uv_val = float(raw_uv_index_str) if raw_uv_index_str not in ['-99.0', 'N/A'] else 'N/A'
    # 這裡可以根據 UV 值判斷等級，或者假設 UV API 返回時已包含等級
    # 為了簡潔，這裡直接顯示數值。如果需要等級判斷，請自行添加邏輯。
    # parsed_and_formatted_info['uv_index'] = str(uv_val) if uv_val != 'N/A' else 'N/A'

    # *** 修改這裡：如果為 'N/A'，則顯示 '無' 或 '-' ***
    if uv_val != 'N/A':
        # 根據 UV 值判斷等級，或者直接顯示數值
        # 這裡為了簡單，直接顯示數值。如果您有等級判斷，可以加上。
        if uv_val > 7:
            parsed_and_formatted_info['uv_index'] = f"{int(uv_val)} (高)"
        elif uv_val >= 3:
            parsed_and_formatted_info['uv_index'] = f"{int(uv_val)} (中)"
        elif uv_val >= 1: # 低到中等
            parsed_and_formatted_info['uv_index'] = f"{int(uv_val)} (低)"
        else: # 0
            parsed_and_formatted_info['uv_index'] = "0" # 夜間或非常低
    else:
        parsed_and_formatted_info['uv_index'] = "無"

    logger.info(f"已解析並格式化 {query_location_name} 的即時觀測資料。")
    logger.debug(f"解析後的即時觀測資料: {parsed_and_formatted_info}")
    return parsed_and_formatted_info
    

    parsed_data = {}
    try:
        station_data = None
        for record in cwa_data.get('records', {}).get('Station', []):
            if record.get('StationName') == location_name or \
               record.get('LocationName') == location_name:
                station_data = record
                break

        if station_data:
            parsed_data['temperature'] = 'N/A'
            parsed_data['humidity'] = 'N/A'
            parsed_data['wind_speed'] = 'N/A'
            parsed_data['pressure'] = 'N/A'

            for element in station_data.get('WeatherElement', []):
                if element.get('ElementName') == 'TEMP':
                    parsed_data['temperature'] = element.get('Value', 'N/A')
                elif element.get('ElementName') == 'HUMD':
                    try:
                        value = float(element.get('Value'))
                        parsed_data['humidity'] = f"{value * 100:.0f}"
                    except (ValueError, TypeError):
                        parsed_data['humidity'] = 'N/A'
                elif element.get('ElementName') == 'WIND_SPEED':
                    parsed_data['wind_speed'] = element.get('Value', 'N/A')
                elif element.get('ElementName') == 'PRES':
                    parsed_data['pressure'] = element.get('Value', 'N/A')

            parsed_data['weather_description'] = "數據暫無描述" # 根據實際情況填充

            logger.info(f"已解析 {location_name} 的即時天氣資料。")
        else:
            logger.warning(f"在即時觀測數據中找不到 {location_name} 的資料。")

    except Exception as e:
        logger.error(f"解析即時天氣資料時發生錯誤: {e}")
        return {}
    return parsed_data