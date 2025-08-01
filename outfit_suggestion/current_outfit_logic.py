# outfit_suggestion/current_outfit_logic.py
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
        current_weather_data (dict): 包含 'current_temp_value' (當前溫度，數值),
                                     'sensation_temp_value' (體感溫度，數值),
                                     'precipitation_value' (降水量，數值),
                                     'weather_description' (天氣現象，如晴、陰、雨),
                                     'humidity_value' (相對濕度，數值),
                                     'uv_index_value' (紫外線指數，數值),
                                     'wind_speed_ms_value' (風速，m/s 數值),
                                     'beaufort_scale_int' (蒲福風級數字),
                                     'wind_speed_beaufort_display' (組合的蒲福風級顯示字串)
                                     等資訊。
                                     這是 weather_current_parser.py 輸出後的格式。
    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """
    # 從傳入的字典中直接獲取數值型別的數據
    raw_time_str = current_weather_data.get('observation_time', 'N/A')
    weather_phenomenon = current_weather_data.get('weather_description', '晴')

    # 直接獲取數值型別的數據，如果沒有則預設為 None 或 0
    temp = current_weather_data.get('current_temp_value')
    feels_like = current_weather_data.get('sensation_temp_value')
    humidity = current_weather_data.get('humidity_value')
    precipitation_value = current_weather_data.get('precipitation_value', 0.0)
    # wind_speed_ms = current_weather_data.get('wind_speed_ms_value', 0.0)
    uv_index = current_weather_data.get('uv_index_value', 0)
    uv_index_display = current_weather_data.get('uv_index')

    # 獲取蒲福風級相關資訊，直接用於顯示
    beaufort_scale_int = current_weather_data.get('beaufort_scale_int', 0) # 蒲福風級數字
    wind_speed_beaufort_display = current_weather_data.get('wind_speed_beaufort_display', 'N/A') # 組合後的顯示字串
    
    # 如果體感溫度仍為None，則使用實際溫度（如果存在）
    if feels_like is None and temp is not None:
        feels_like = temp
    
    # 如果兩者都為 None，則預設一個值以避免錯誤
    if feels_like is None:
        feels_like = 25 # 預設一個溫和的溫度，以便後續判斷能繼續

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
    if precipitation_value >= 40.0: # 參考台灣中央氣象署豪雨標準：24小時累積雨量達80毫米以上，或1小時累積雨量達40毫米以上
        suggestion_text.append("• 降雨量極大，外出務必攜帶雨具，建議穿著防水性極佳的衣物及鞋子，並注意行車安全。")
        suggestion_image_url = IMAGE_URLS["HEAVY_RAIN"]
    elif precipitation_value >= 15.0: # 參考台灣中央氣象署大雨標準：24小時累積雨量達50毫米以上，或1小時累積雨量達15毫米以上
        suggestion_text.append("• 降雨量大，外出務必攜帶雨具，建議穿著防水性佳的衣物及鞋子。")
        suggestion_image_url = IMAGE_URLS["HEAVY_RAIN"] # 可以考慮用不同的重雨圖
    elif precipitation_value > 5.0: # 中雨，假設5mm以上為中雨
        suggestion_text.append("• 有中等降雨，建議攜帶雨具，穿著防潑水衣物或備薄外套。")
        suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]
    elif precipitation_value > 0 and precipitation_value <= 5.0: # 小雨/毛毛雨
        suggestion_text.append("• 有小雨，外出建議攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["LIGHT_RAIN"] # 或者更適合的小雨圖
    elif "午後雷陣雨" in weather_phenomenon:
        suggestion_text.append("• 午後可能有雷陣雨，外出請攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["LIGHT_RAIN"] # 或者更適合的雷陣雨圖
    elif "陣雨" in weather_phenomenon or "雷雨" in weather_phenomenon or "雨" in weather_phenomenon:
        suggestion_text.append("• 局部地區可能有短暫降雨，外出建議攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]
    else:
        # 如果 weather_phenomenon 沒有雨，且 precipitation_value 為 0
        # 這裡可以補充沒有降雨的建議，或者不做任何操作（如果只關心降雨情況）
        pass

    # --- 補充濕度建議 ---
    if humidity is not None:
        if humidity >= 85:
            suggestion_text.append("• 濕度極高，體感可能悶熱或濕冷，建議選擇吸濕排汗的衣物。")
            if suggestion_image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_HUMIDITY"] # 高濕度圖
        elif humidity >= 70:
            if feels_like is not None and feels_like >= 25:
                suggestion_text.append("濕度偏高且氣溫較高，體感可能較為悶熱，建議穿著寬鬆、透氣的衣物。")
            else:
                suggestion_text.append("濕度偏高，空氣較為潮濕，注意衣物選擇透氣性。")
        elif humidity < 40:
            suggestion_text.append("空氣較為乾燥，注意肌膚保濕，可考慮攜帶護手霜或補水用品。")
            if suggestion_image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                suggestion_image_url = IMAGE_URLS["DRY_WEATHER"] # 乾燥天氣圖

    # --- 補充風速/風寒建議 (使用蒲福風級數字判斷和描述) ---
    if beaufort_scale_int is not None and feels_like is not None: # 確保這些值不是None
        if beaufort_scale_int >= 7 and feels_like < 20: # 疾風或更高，且氣溫偏涼
            suggestion_text.append(f"• 風力屬於 {wind_speed_beaufort_display}，風寒效應明顯，請特別注意防風保暖，可考慮穿著防風外套。")
            if feels_like < 15:
                suggestion_text.append("• 尤其注意頭部、頸部保暖。")
            suggestion_image_url = IMAGE_URLS["WINDY"]
        elif beaufort_scale_int >= 5 and feels_like < 25: # 清風或更高，且氣溫偏涼
            suggestion_text.append(f"• 風力屬於 {wind_speed_beaufort_display}，體感溫度可能略低，可備一件薄防風外套。")
            suggestion_image_url = IMAGE_URLS["WINDY"]
        elif beaufort_scale_int >= 3 and feels_like < 15: # 微風或更高，但氣溫較低
            suggestion_text.append(f"• 風力屬於 {wind_speed_beaufort_display}，雖然風不大但天氣微涼，請注意保暖。")
        else: # 0-2級，微風以下
            suggestion_text.append("• 今日風力較弱，穿搭上無需特別考慮風速影響。")

    # --- 補充紫外線指數建議 ---
    if uv_index is not None: # 確保 uv_index 不是None
        if uv_index >= 11:
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_display}！戶外活動務必全程做好防曬，包括防曬乳、帽子、太陽眼鏡、遮陽傘，建議穿著長袖、輕薄透氣的衣物。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["HOT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"] # 繼續使用高紫外線圖片
        elif uv_index >= 8:
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_display}！長時間戶外活動請加強防曬，建議戴太陽眼鏡、遮陽帽，塗抹防曬乳。")
            if feels_like is not None and feels_like >= 25: # 在炎熱天氣下，紫外線更需要強調防曬衣物
                suggestion_text.append("• 可考慮穿著防曬衣物。")
            suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index >= 6:
            suggestion_text.append(f"• 紫外線指數為 {uv_index_display}，外出建議戴太陽眼鏡、遮陽帽，並塗抹防曬乳。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index >= 3:
            suggestion_text.append(f"• 紫外線指數為 {uv_index_display}，外出可戴太陽眼鏡。")
    else:
        suggestion_text.append("• 紫外線指數資訊不完整。")

    # 如果沒有特定建議，給出預設文字
    if not suggestion_text:
        suggestion_text.append("• 今天天氣狀況良好，穿著舒適即可。")
        if suggestion_image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            suggestion_image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # final_suggestion = " ".join(suggestion_text)

    # --- 回傳所有需要顯示在 Flex Message 中的天氣數據 ---
    # 直接使用 current_weather_data 中已經格式化好的字串，或解析好的數值
    outfit_info_to_return = {
        "observation_time": raw_time_str,
        "suggestion_text": suggestion_text,
        "suggestion_image_url": suggestion_image_url,
        "weather_condition": weather_phenomenon,
        # "current_temp": current_weather_data.get('current_temp', 'N/A'), # 使用已格式化的字串
        "feels_like": current_weather_data.get('sensation_temp_display', 'N/A'), # 使用已格式化的字串
        "humidity": current_weather_data.get('humidity', 'N/A'), # 使用已格式化的字串
        "precipitation": current_weather_data.get('precipitation', 'N/A'), # 使用已格式化的字串
        "wind_speed_beaufort_display": wind_speed_beaufort_display, # 使用蒲福風級顯示字串
        # "wind_direction": current_weather_data.get('wind_direction', 'N/A'), # 使用已格式化的字串
        "uv_index": current_weather_data.get('uv_index', 'N/A'), # 使用已格式化的字串
        #"pressure": current_weather_data.get('pressure', 'N/A') # 使用已格式化的字串
    }

    logger.debug(f"即時穿搭建議生成及數據回傳: {outfit_info_to_return}")
    return outfit_info_to_return