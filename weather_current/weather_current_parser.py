# weather_current/weather_current_parser.py
"""
解析中央氣象署的即時天氣觀測資料（O-A0003-001）。
從原始的 JSON 數據中提取關鍵的天氣元素，並將其處理、計算和格式化，讓 LINE Flex Message 直接使用。
主要職責：
1. 體感溫度、風向、風速蒲福風級的計算。
2. 將原始數值數據轉換為易於閱讀的格式（如加上單位、描述）。
3. 處理數據缺失或異常的情況，並提供預設值。
"""
import logging
from datetime import datetime
from utils.weather_utils import get_beaufort_scale_description, convert_ms_to_beaufort_scale

logger = logging.getLogger(__name__)

# --- 計算簡化版的體感溫度（熱指數) ---
def calculate_apparent_temperature(temp_c: float, humidity_percent: float) -> float | str:
    """
    根據氣溫和相對濕度來估算人體感受到的溫度。
    採用美國國家氣象局的熱指數公式簡化版本。
    如果溫度較低（低於華氏 80 度），則熱指數意義不大，直接回傳實際氣溫。
    """
    # 檢查輸入的溫度和濕度是否為有效數字，如果不是則回傳"無資料"
    if not isinstance(temp_c, (int, float)) or not isinstance(humidity_percent, (int, float)):
        return "無資料"

    # 將濕度從百分比轉換為小數
    humidity = humidity_percent / 100.0

    # 將攝氏度轉換為華氏度 (熱指數公式常用華氏度)
    temp_f = (temp_c * 9/5) + 32

    # 如果溫度較低，直接返回實際溫度或進行風寒計算
    # 低溫時熱指數不適用，體感溫度通常等於實際溫度，或應考慮風寒
    if temp_f < 80:
        return round(temp_c, 1) # 在較低溫時，熱指數意義不大，直接返回實際溫度

    # 這是美國國家氣象局的熱指數公式，用於計算在高溫高濕環境下的體感溫度
    apparent_temp_f = -42.379 + 2.04901523*temp_f + 10.14333127*humidity - 0.22475541*temp_f*humidity - 6.83783e-3*temp_f**2 - 5.481717e-2*humidity**2 + 1.22874e-3*temp_f**2*humidity + 8.5282e-4*temp_f*humidity**2 - 1.99e-6*temp_f**2*humidity**2

    # 將華氏度轉換回攝氏度
    apparent_temp_c = (apparent_temp_f - 32) * 5/9

    # 如果計算結果與實際溫度小於 1 度，直接返回實際溫度
    if abs(apparent_temp_c - temp_c) < 1.0:
        return round(temp_c, 1)

    return round(apparent_temp_c, 1)

# --- 將風向的角度值轉換為八方位的中文描述 ---
def get_wind_direction_description(degrees: float | str) -> str:
    """
    這個函式將 360 度的角度值映射到「北」、「東北」、「東」等中文描述。
    """
    # 檢查輸入是否為有效數字，如果不是則回傳"無資料"
    if not isinstance(degrees, (int, float)):
        return "無資料"

    directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
    """
    根據角度計算對應的方位索引。
    將 360 度圓分成 8 個 45 度的扇區，並加上 22.5 度偏移來對齊扇區中心。
    然後使用模運算 (%) 確保索引值在 0 到 7 之間。
    """
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]
    
# --- 解析中央氣象署 O-A0003-001 (有人氣象站資料) 的原始 JSON 數據 ---
def parse_current_weather(cwa_data: dict, query_location_name: str) -> dict | None: # 修改返回類型提示
    """
    從 CWA API 獲取的原始數據中，提取指定地點的即時天氣資訊，並將這些資訊進行計算、格式化，生成一個可以直接用於顯示的字典。
    如果找不到指定地點的數據，會回傳 None。

    Args:
        cwa_data (dict): 從 CWA API 獲取的原始 JSON 數據。
        query_location_name (str): 用戶查詢的地點名稱，用於匹配資料。
        
    Returns:
        dict: 包含解析並完全格式化後天氣數據的字典，如果找不到數據則為 None。
    """
    # 驗證 API 回應的成功狀態
    if not cwa_data or cwa_data.get('success') != 'true' or \
       'records' not in cwa_data or 'Station' not in cwa_data['records']:
        logger.warning("即時觀測數據格式不正確或缺少關鍵鍵，無法解析。")
        return None # 如果數據無效、缺少成功標誌或關鍵的 'Station' 鍵，則記錄警告並返回 None
    
    target_station_data = None

    # 遍歷所有測站，尋找匹配的地點
    # 程式碼會逐一檢查每個測站的名稱（StationName）是否與用戶查詢的地點名稱（query_location_name）相符
    for station in cwa_data['records']['Station']:
        # 使用 StationName 進行匹配
        if station.get('StationName') == query_location_name:
            target_station_data = station
            break

    # 如果找不到精確匹配，則嘗試使用第一個測站的數據作為 fallback
    if not target_station_data and cwa_data['records']['Station']:
        target_station_data = cwa_data['records']['Station'][0]
        logger.warning(f"未找到精確匹配地點 '{query_location_name}' 的觀測站，將使用第一個觀測站 '{target_station_data.get('StationName', '未知')}' 的數據。")

    # 如果在所有測站中都找不到數據，則記錄警告並返回 None
    if not target_station_data:
        logger.warning(f"在即時觀測數據中找不到 '{query_location_name}' 或任何測站的資料。")
        return None
    
    # 提取原始天氣元素
    obs_time_str = target_station_data.get('ObsTime', {}).get('DateTime')
    weather_elements = target_station_data.get('WeatherElement', {})
    
    # 初始化一個字典來存放所有解析和最終格式化後的數據
    parsed_and_formatted_info = {}

    # --- 觀測時間處理與格式化 ---
    """
    原始時間字串是 ISO 8601 格式，程式會轉換為 datetime 物件，然後格式化成更易於閱讀的中文日期和時間格式，例如 "2025年8月20日 (三) 22:16"。
    """
    if obs_time_str and obs_time_str != '-99':
        try:
            # 處理 ISO 8601 格式，確保時區資訊被正確處理
            obs_datetime_obj = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))

            weekday_map = {
            0: "一", 1: "二", 2: "三", 3: "四",
            4: "五", 5: "六", 6: "日"
            }

            chinese_weekday = weekday_map.get(obs_datetime_obj.weekday(), "")

            # 格式化日期字串 (兼容不同系統的 strftime 格式)
            try:
                # 嘗試使用 %-m 和 %-d (Linux/macOS 兼容)
                formatted_date_part = obs_datetime_obj.strftime("%Y年%-m月%-d日") 
            except ValueError:
                # 如果失敗 (如在 Windows 上)，使用 %m 和 %d
                formatted_date_part = obs_datetime_obj.strftime("%Y年%m月%d日")

            # 格式化時間部分
            formatted_time_part = obs_datetime_obj.strftime('%H:%M')

            # 組合成用於顯示的日期和星期幾格式
            parsed_and_formatted_info['observation_time'] = \
                f"日期：{formatted_date_part} ({chinese_weekday}) {formatted_time_part}"

        except ValueError:
            logger.warning(f"無法解析或格式化日期: {obs_time_str}")
            parsed_and_formatted_info['observation_time'] = "未知日期" # 解析失敗，設定為 "未知日期"
    else:
        parsed_and_formatted_info['observation_time'] = "未知日期"

    # --- 提取、計算並最終格式化其他天氣元素 ---
    # 天氣描述 (Weather)
    # 直接從 JSON 中提取天氣描述，如果沒有則使用 "無資料"
    parsed_and_formatted_info['weather_description'] = weather_elements.get('Weather', '無資料')

    # 氣溫 (AirTemperature)
    """
    將原始的氣溫字串轉換為浮點數。
    如果轉換成功，將格式化後的字串（例如 "25.5°C"）和原始數值都儲存起來，這樣數值可以用於後續的計算（如體感溫度）。
    如果數據無效，則會記錄警告並設置為 "無資料"。
    """
    raw_temp_str = weather_elements.get('AirTemperature')
    temp_val = None
    if raw_temp_str is not None and raw_temp_str.strip() not in ['', '-99.0', '無資料'] and raw_temp_str.replace('.', '', 1).isdigit():
        try:
            temp_val = float(raw_temp_str)
            parsed_and_formatted_info['current_temp'] = f"{round(temp_val, 1)}°C"
            parsed_and_formatted_info['current_temp_value'] = temp_val # 儲存原始數值
        except ValueError:
            logger.warning(f"無法將氣溫 '{raw_temp_str}' 轉換為浮點數。")
    else:
        parsed_and_formatted_info['current_temp'] = '無資料'
        parsed_and_formatted_info['current_temp_value'] = None # 原始數值為 None
    
    # 濕度 (RelativeHumidity)
    """
    與氣溫處理類似，程式會將原始字串轉換為浮點數，並將格式化後的百分比字串和原始數值分別儲存。
    這樣能夠使用原始數值進行體感溫度的計算。
    """
    raw_humidity_str = weather_elements.get('RelativeHumidity')
    hum_val = None
    if raw_humidity_str is not None and raw_humidity_str.strip() not in ['', '-99.0', '無資料'] and raw_humidity_str.isdigit():
        try:
            hum_val = float(raw_humidity_str)
            parsed_and_formatted_info['humidity'] = f"{round(hum_val)}%"
            parsed_and_formatted_info['humidity_value'] = hum_val # 儲存原始數值
        except ValueError:
            logger.warning(f"無法將濕度 '{raw_humidity_str}' 轉換為浮點數。")
    else:
        parsed_and_formatted_info['humidity'] = '無資料'
        parsed_and_formatted_info['humidity_value'] = None # 原始數值為 None

    # 計算體感溫度 (sensation_temp_display 和 sensation_temp_value)
    """
    調用 calculate_apparent_temperature 函式來計算體感溫度。
    檢查計算出的體感溫度與實際溫度之間的差異。
    如果差異大於或等於 1 度，會顯示計算出的體感溫度。
    如果差異很小，則會顯示 "與實際溫度相近"。
    """
    calculated_apparent_temp = '無資料' # 體感溫度原始數值
    sensation_temp_display = '無資料'   # 格式化後的體感溫度
    sensation_temp_value = None        # 體感溫度原始數值

    if temp_val is not None and hum_val is not None:
        calculated_apparent_temp = calculate_apparent_temperature(temp_val, hum_val)
        if isinstance(calculated_apparent_temp, float):
            sensation_temp_value = calculated_apparent_temp # 儲存原始數值
            # 如果體感溫度與實際溫度差異達到 1 度或以上，則顯示體感溫度
            if abs(calculated_apparent_temp - temp_val) >= 1.0:
                sensation_temp_display = f"{calculated_apparent_temp:.1f}°C"
            else:
                sensation_temp_display = "與實際溫度相近"
    
    parsed_and_formatted_info['sensation_temp_display'] = sensation_temp_display
    parsed_and_formatted_info['sensation_temp_value'] = sensation_temp_value

    # 降雨量 (Precipitation)
    """
    處理 API 可能回傳的 '-99.0' 或 '無資料' 等無效值。
    將降雨量字串轉換為浮點數，並根據數值進行邏輯判斷。
    如果降雨量小於等於 0.1 mm，則顯示為 "無"；否則，顯示具體的降雨量數值和單位。
    """
    raw_precipitation_str = weather_elements.get('Now', {}).get('Precipitation', '無資料')
    prec_val = None
    if raw_precipitation_str not in ['-99.0', '無資料']:
        try:
            prec_val = float(raw_precipitation_str)
            parsed_and_formatted_info['precipitation_value'] = prec_val # 儲存原始數值
            if prec_val <= 0.1: # 幾乎無降雨，顯示 "無"
                parsed_and_formatted_info['precipitation'] = "無"
            else:
                parsed_and_formatted_info['precipitation'] = f"{prec_val} mm"
        except ValueError:
            logger.warning(f"無法將降雨量 '{raw_precipitation_str}' 轉換為浮點數。")
            parsed_and_formatted_info['precipitation'] = "無資料" # 解析失敗或無數據
            parsed_and_formatted_info['precipitation_value'] = 0.0 # 原始數值為 0.0
    else:
        parsed_and_formatted_info['precipitation'] = "無資料"
        parsed_and_formatted_info['precipitation_value'] = 0.0

    # 風速 (WindSpeed) 和風向 (WindDirection)
    """
    分別處理風速和風向的字串，並轉換為浮點數。
    對於風速，會調用外部函式將 m/s 轉換為蒲福風級，並生成包含級數和描述的格式化字串。
    對於風向，會調用 get_wind_direction_description 函式將角度轉換為中文方向描述。
    """
    raw_wind_speed_str = weather_elements.get('WindSpeed')
    raw_wind_direction_str = weather_elements.get('WindDirection')
    
    wind_speed_val = None                 # 風速 m/s 數值
    beaufort_scale_int = None             # 蒲福風級數字
    beaufort_scale_desc = '無資料'         # 蒲福風級描述
    wind_speed_beaufort_display = '無資料' # 組合後的顯示字串

    wind_direction_val = None              # 風向角度數值
    wind_direction_desc = '無資料'          # 方向描述

    if raw_wind_speed_str is not None and raw_wind_speed_str.strip() not in ['', '-99.0', '無資料'] and raw_wind_speed_str.replace('.', '', 1).isdigit():
        try:
            wind_speed_val = float(raw_wind_speed_str)

            # 計算並取得蒲福風級描述
            beaufort_scale_int = convert_ms_to_beaufort_scale(wind_speed_val)
            beaufort_scale_desc = get_beaufort_scale_description(beaufort_scale_int)
            wind_speed_beaufort_display = f"{beaufort_scale_int} 級 ({beaufort_scale_desc})"

            parsed_and_formatted_info['wind_speed_ms_value'] = wind_speed_val      # 儲存 m/s 數值
            parsed_and_formatted_info['beaufort_scale_int'] = beaufort_scale_int   # 儲存蒲福風級數字
            parsed_and_formatted_info['beaufort_scale_desc'] = beaufort_scale_desc # 儲存蒲福風級描述
            parsed_and_formatted_info['wind_speed_beaufort_display'] = wind_speed_beaufort_display # 儲存組合顯示字串
        except ValueError:
            logger.warning(f"無法將風速 '{raw_wind_speed_str}' 轉換為浮點數。")
            parsed_and_formatted_info['wind_speed_ms_value'] = 0.0
            parsed_and_formatted_info['beaufort_scale_int'] = 0
            parsed_and_formatted_info['wind_speed_beaufort_display'] = '無資料'
    else:
        parsed_and_formatted_info['wind_speed_ms_value'] = 0.0
        parsed_and_formatted_info['beaufort_scale_int'] = 0
        parsed_and_formatted_info['wind_speed_beaufort_display'] = '無資料'
    
    if raw_wind_direction_str is not None and raw_wind_direction_str.strip() not in ['', '-99.0', '無資料'] and raw_wind_direction_str.replace('.', '', 1).isdigit():
        try:
            wind_direction_val = float(raw_wind_direction_str)
            wind_direction_desc = get_wind_direction_description(wind_direction_val)
            parsed_and_formatted_info['wind_direction'] = wind_direction_desc # 儲存方向描述
        except ValueError:
            logger.warning(f"無法將風向 '{raw_wind_direction_str}' 轉換為浮點數。")
            parsed_and_formatted_info['wind_direction'] = '無資料'
    else:
        parsed_and_formatted_info['wind_direction'] = '無資料'

    # 氣壓 (AirPressure)
    """
    將原始字串轉換為浮點數，並格式化為帶有 "hPa" 單位的字串。
    """
    raw_pressure_str = weather_elements.get('AirPressure', '-99.0')
    pres_val = None
    if raw_pressure_str not in ['-99.0', '無資料']:
        try:
            pres_val = float(raw_pressure_str)
            parsed_and_formatted_info['pressure'] = f"{pres_val} hPa"
            parsed_and_formatted_info['pressure_value'] = pres_val # 儲存原始數值
        except ValueError:
            logger.warning(f"無法將氣壓 '{raw_pressure_str}' 轉換為浮點數。")
            parsed_and_formatted_info['pressure'] = '無資料'
            parsed_and_formatted_info['pressure_value'] = None
    else:
        parsed_and_formatted_info['pressure'] = '無資料'
        parsed_and_formatted_info['pressure_value'] = None

    # 紫外線指數 (UVIndex)
    """
    將原始字串轉換為浮點數並根據數值大小進行分級。
    根據不同的級別，生成不同的描述性字串（例如 "高"、"過量"、"危險"）。
    """
    raw_uv_index_str = weather_elements.get('UVIndex', '-99.0')
    uv_val = None
    uv_index_display = '無資料'
    if raw_uv_index_str not in ['-99.0', '無資料']:
        try:
            uv_val = float(raw_uv_index_str)
            parsed_and_formatted_info['uv_index_value'] = int(uv_val) # 儲存整數數值

            if uv_val >= 11:
                uv_index_display = f"{int(uv_val)} (危險)"
            elif uv_val >= 8:
                uv_index_display = f"{int(uv_val)} (過量)"
            elif uv_val >= 6:
                uv_index_display = f"{int(uv_val)} (高)"
            elif uv_val >= 3:
                uv_index_display = f"{int(uv_val)} (中)"
            elif uv_val >= 0: # 包含 0-2 的低級
                uv_index_display = f"{int(uv_val)} (低)"
            else: # 考慮負值或其他異常情況
                uv_index_display = "無資料"

            parsed_and_formatted_info['uv_index'] = uv_index_display # 儲存格式化字串
        
        except ValueError:
            logger.warning(f"無法將紫外線指數 '{raw_uv_index_str}' 轉換為浮點數。")
            parsed_and_formatted_info['uv_index'] = "無資料"
            parsed_and_formatted_info['uv_index_value'] = 0
    else:
        parsed_and_formatted_info['uv_index'] = "無"
        parsed_and_formatted_info['uv_index_value'] = 0

    parsed_and_formatted_info["location_name"] = query_location_name

    logger.info(f"已解析並格式化 {query_location_name} 的即時觀測資料。")
    logger.debug(f"解析後的即時觀測資料: {parsed_and_formatted_info}")
    return parsed_and_formatted_info