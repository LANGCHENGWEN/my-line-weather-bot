# utils/current_outfit_logic.py
import logging

logger = logging.getLogger(__name__)

IMAGE_URLS = {
    #"NO_DATA": "https://i.imgur.com/no_data.png",
    "DEFAULT": "https://i.imgur.com/current_default.png",
    "HOT": "https://i.imgur.com/hot_weather_outfit.png",
    "WARM": "https://i.imgur.com/warm_weather_outfit.png",
    "COOL": "https://i.imgur.com/cool_weather_outfit.png",
    "CHILLY": "https://i.imgur.com/chilly_weather_outfit.png",
    "COLD": "https://i.imgur.com/cold_weather_outfit.png",
    "FREEZING": "https://i.imgur.com/freezing_weather_outfit.png",
    "HEAVY_RAIN": "https://i.imgur.com/heavy_rain.png",
    "RAINY_CURRENT": "https://i.imgur.com/rainy_current.png",
    "LIGHT_RAIN": "https://i.imgur.com/light_rain.png",
    "COMFORTABLE": "https://i.imgur.com/comfortable_weather.png",

    "HIGH_HUMIDITY": "https://i.imgur.com/high_humidity.png",
    "DRY_WEATHER": "https://i.imgur.com/dry_weather.png",
    "WINDY": "https://i.imgur.com/windy_outfit.png",
    "HIGH_UVI": "https://i.imgur.com/high_uvi.png"
}

def get_outfit_suggestion_for_current_weather(current_weather_data: dict) -> dict:
    """
    根據即時天氣數據 (來自 weather_current_parser.py 的輸出格式) 提供穿搭建議。
    Args:
        current_weather_data (dict): 包含 'current_temp' (當前溫度，含單位),
                                     'sensation_temp_display' (體感溫度顯示，含單位或描述),
                                     'precipitation' (降水量，含單位或"無"),
                                     'weather_description' (天氣現象，如晴、陰、雨),
                                     'humidity' (相對濕度，含單位),
                                     'uv_index' (紫外線指數，含描述),
                                     'wind_speed' (風速，含單位),
                                     'wind_direction' (風向) 等資訊。
                                     這是 weather_current_parser.py 輸出後的格式。
    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """
    # 從傳入的字典中獲取原始值 (注意這些都是字串，需要解析)
    raw_time_str = current_weather_data.get('observation_time', 'N/A')
    weather_phenomenon = current_weather_data.get('weather_description', '晴')
    raw_temp_str = current_weather_data.get('current_temp', 'N/A')
    raw_sensation_temp_str = current_weather_data.get('sensation_temp_display', 'N/A')
    raw_humidity_str = current_weather_data.get('humidity', 'N/A')
    raw_precipitation_str = current_weather_data.get('precipitation', '無')
    raw_wind_speed_str = current_weather_data.get('wind_speed', '0.0 m/s')
    raw_uv_index_str = current_weather_data.get('uv_index', '0 (低)')
    
    # --- 解析溫度和體感溫度 ---
    temp = None
    feels_like = None
    humidity = None
    uv_index = 0
    wind_speed = 0.0 # 單位轉換為 m/s
    precipitation_value = 0.0 # 新增：用於儲存解析後的降水量數值

    try:
        if raw_temp_str != 'N/A' and '°C' in raw_temp_str:
            temp = float(raw_temp_str.replace('°C', '').strip())
    except ValueError:
        logger.warning(f"無法解析即時溫度: {raw_temp_str}")

    try:
        if raw_sensation_temp_str != 'N/A' and '°C' in raw_sensation_temp_str:
            feels_like = float(raw_sensation_temp_str.replace('°C', '').strip())
        elif "相近" in raw_sensation_temp_str and temp is not None:
            feels_like = temp # 如果顯示相近，就用實際溫度
    except ValueError:
        logger.warning(f"無法解析體感溫度: {raw_sensation_temp_str}")
    
    # 如果體感溫度仍為None，則使用實際溫度（如果存在）
    if feels_like is None and temp is not None:
        feels_like = temp
    
    # 如果兩者都為 None，則預設一個值以避免錯誤
    if feels_like is None:
        feels_like = 25 # 預設一個溫和的溫度，以便後續判斷能繼續

    try:
        if raw_humidity_str != 'N/A' and '%' in raw_humidity_str:
            humidity = int(raw_humidity_str.replace('%', '').strip())
    except ValueError:
        logger.warning(f"無法解析濕度: {raw_humidity_str}")

    try:
        # 紫外線指數通常是數字和描述 (e.g., "7 (高)")
        uv_index_part = raw_uv_index_str.split(' ')[0]
        uv_index = int(float(uv_index_part)) # 確保能處理浮點數再轉整數
    except (ValueError, IndexError):
        logger.warning(f"無法解析紫外線指數: {raw_uv_index_str}")

    try:
        if raw_wind_speed_str != 'N/A' and 'm/s' in raw_wind_speed_str:
            wind_speed = float(raw_wind_speed_str.replace(' m/s', '').strip())
    except ValueError:
        logger.warning(f"無法解析風速: {raw_wind_speed_str}")

    # 新增：安全地解析降水量
    try:
        if raw_precipitation_str != '無' and 'mm' in raw_precipitation_str:
            precipitation_value = float(raw_precipitation_str.replace(' mm', '').strip())
    except ValueError:
        logger.warning(f"無法解析降水量: {raw_precipitation_str}")
        # 如果解析失敗，或者值為'無'，precipitation_value 保持為 0.0

    suggestion_text = []
    suggestion_image_url = IMAGE_URLS["DEFAULT"] # 預設圖

    # --- 根據體感溫度給出建議 (更詳細) ---
    if feels_like is not None:
        if feels_like >= 32:
            suggestion_text.append("• 天氣極度炎熱，請務必穿著最輕薄、透氣的衣物。")
            suggestion_image_url = IMAGE_URLS["HOT"]
        elif 28 <= feels_like < 32:
            suggestion_text.append("• 天氣炎熱，建議穿著涼爽的短袖、短褲或裙子。")
            suggestion_image_url = IMAGE_URLS["HOT"]
        elif 24 <= feels_like < 28:
            suggestion_text.append("• 天氣溫暖舒適，穿著短袖即可，室內外溫差大，可備薄外套。")
            suggestion_image_url = IMAGE_URLS["WARM"]
        elif 19 <= feels_like < 24:
            suggestion_text.append("• 天氣涼爽，建議穿著薄長袖上衣或薄外套，夜晚可能稍涼。")
            suggestion_image_url = IMAGE_URLS["COOL"]
        elif 14 <= feels_like < 19:
            suggestion_text.append("• 天氣微涼，建議穿著毛衣或較厚的外套，注意保暖。")
            suggestion_image_url = IMAGE_URLS["CHILLY"]
        elif 10 <= feels_like < 14:
            suggestion_text.append("• 天氣寒冷，請穿著厚外套、毛衣，務必注意保暖。")
            suggestion_image_url = IMAGE_URLS["COLD"]
        else: # feels_like < 10
            suggestion_text.append("• 天氣非常寒冷，建議穿著羽絨外套、厚毛衣、圍巾、手套，做好全面保暖！")
            suggestion_image_url = IMAGE_URLS["FREEZING"]

    # --- 針對降雨情況進行補充 (更詳細) ---
    if "豪雨" in weather_phenomenon or "大雨" in weather_phenomenon or precipitation_value > 5.0: # 假定5mm以上為大雨
        suggestion_text.append("• 降雨機率極高，外出務必攜帶雨具，建議穿著防水性佳的衣物及鞋子。")
        suggestion_image_url = IMAGE_URLS["HEAVY_RAIN"]
    elif "午後雷陣雨" in weather_phenomenon:
        suggestion_text.append("• 午後有雷陣雨，外出請攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["LIGHT_RAIN"] # 或者更適合的雷陣雨圖
    elif "陣雨" in weather_phenomenon or "雷雨" in weather_phenomenon or "雨" in weather_phenomenon:
        # 這裡可以根據 precipitation_value 再次細分小雨、中雨
        if precipitation_value > 0 and precipitation_value <= 5.0: # 假設 0-5mm 為一般雨
            suggestion_text.append("• 降雨機率較高，建議攜帶雨具，穿著防潑水衣物或備薄外套。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]
        elif precipitation_value == 0 and ("陣雨" in weather_phenomenon or "雨" in weather_phenomenon):
            # 描述有雨但降水量為0，可能是短暫或預期有雨但尚未發生
            suggestion_text.append("• 可能有短暫降雨，建議攜帶雨具。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]

    # --- 補充濕度建議 ---
    if humidity is not None:
        if humidity > 85:
            suggestion_text.append("• 濕度極高，體感可能悶熱或濕冷，建議選擇吸濕排汗的衣物。")
        elif humidity > 70 and feels_like >= 25:
            suggestion_text.append("• 濕度偏高，體感可能較悶熱，建議穿著透氣寬鬆的衣物。")
        elif humidity < 40:
            suggestion_text.append("• 天氣較乾燥，可考慮攜帶保濕用品。")

    # --- 補充風速/風寒建議 ---
    if wind_speed is not None and feels_like is not None: # 確保這些值不是None
        if wind_speed >= 7.0 and feels_like < 20: # 風速大於 7m/s 且氣溫偏涼
            suggestion_text.append(f"• 風速較大 ({wind_speed}級)，風寒效應明顯，請特別注意防風保暖，可考慮穿著防風外套。")
            if feels_like < 15:
                suggestion_text.append("• 尤其注意頭部、頸部保暖。")
        elif wind_speed >= 5.0 and feels_like < 25:
            suggestion_text.append(f"• 風勢稍強 ({wind_speed}級)，體感溫度可能略低，可備一件薄防風外套。")

    # --- 補充紫外線指數建議 ---
    if uv_index is not None: # 確保 uv_index 不是None
        if uv_index >= 8:
            suggestion_text.append("• 紫外線極高，外出務必防曬，戴帽、太陽眼鏡、擦防曬乳，避免長時間曝曬。")
            if feels_like is not None and feels_like >= 25: # 在炎熱天氣下，紫外線更需要強調防曬衣物
                suggestion_text.append("• 可考慮穿著防曬衣物。")
        elif uv_index >= 6:
            suggestion_text.append("• 紫外線高，外出建議做好防曬措施。")
        elif uv_index >= 3:
            suggestion_text.append("• 紫外線中等，適度防曬即可。")

    # 如果沒有特定建議，給出預設文字
    if not suggestion_text:
        suggestion_text.append("• 今天天氣狀況良好，穿著舒適即可。")
        if suggestion_image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            suggestion_image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # --- 關鍵修正：將數值轉換為帶有單位的字串 ---
    formatted_feels_like = f"{round(feels_like, 1)}°C" if feels_like is not None else "N/A"
    formatted_humidity = f"{round(humidity)}%" if humidity is not None else "N/A"
    formatted_wind_speed = f"{round(wind_speed, 1)} m/s" if wind_speed is not None else "N/A"
    
    # 紫外線指數處理需要更精細，因為它包含數字和描述
    formatted_uv_index = "N/A"
    if uv_index is not None:
        # 嘗試從原始字串中保留描述，如果原始字串格式不對，就只顯示數字
        if '(' in raw_uv_index_str and ')' in raw_uv_index_str:
            formatted_uv_index = raw_uv_index_str
        else:
            # 根據數值重新判斷描述
            if uv_index >= 11:
                formatted_uv_index = f"{uv_index} (危險)"
            elif uv_index >= 8:
                formatted_uv_index = f"{uv_index} (過量)"
            elif uv_index >= 6:
                formatted_uv_index = f"{uv_index} (高)"
            elif uv_index >= 3:
                formatted_uv_index = f"{uv_index} (中)"
            else:
                formatted_uv_index = f"{uv_index} (低)"

    # 新增：格式化降水量。只有當降水量不為零時才顯示單位。
    formatted_precipitation = ""
    if precipitation_value > 0:
        formatted_precipitation = f"{round(precipitation_value, 1)} mm"
    else:
        if raw_precipitation_str == '無':
            formatted_precipitation = "無"
        else: # 可能是無法解析的非零字串
            formatted_precipitation = raw_precipitation_str

    # final_suggestion = " ".join(suggestion_text)

    # --- 關鍵修改：回傳所有需要顯示在 Flex Message 中的天氣數據 ---
    outfit_info_to_return = {
        "observation_time": raw_time_str,
        "suggestion_text": suggestion_text,
        "suggestion_image_url": suggestion_image_url,
        # 將解析後或處理過的天氣數據傳遞出去
        "weather_condition": weather_phenomenon, # 確保使用正確的變數名
        "feels_like": formatted_feels_like,
        "humidity": formatted_humidity,
        "precipitation": formatted_precipitation,
        "wind_speed": formatted_wind_speed,
        "uv_index": formatted_uv_index
    }

    logger.debug(f"即時穿搭建議生成及數據回傳: {outfit_info_to_return}")
    return outfit_info_to_return