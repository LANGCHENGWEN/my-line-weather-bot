# outfit_suggestion/forecast_outfit_logic.py
import logging

logger = logging.getLogger(__name__)

IMAGE_URLS = {
    "NO_DATA": "https://i.imgur.com/no_data.png",
    "DEFAULT": "https://i.imgur.com/forecast_default.png",
    "HOT": "https://i.imgur.com/hot_weather_outfit.png",
    "COLD": "https://i.imgur.com/cold_weather_outfit.png",
    "HEAVY_RAIN": "https://i.imgur.com/heavy_rain.png",
    "RAINY_FORECAST": "https://i.imgur.com/rainy_forecast.png",
    "LIGHT_RAIN": "https://i.imgur.com/light_rain.png",
    "WARM": "https://i.imgur.com/warm_weather_outfit.png",
    "COOL": "https://i.imgur.com/cool_weather_outfit.png",
    "COMFORTABLE": "https://i.imgur.com/comfortable_weather.png",
    "HIGH_HUMIDITY": "https://i.imgur.com/high_humidity.png",
    "DRY_WEATHER": "https://i.imgur.com/dry_weather.png",
    "WINDY": "https://i.imgur.com/windy_outfit.png",
    "HIGH_UVI": "https://i.imgur.com/high_uvi.png"
}

def get_outfit_suggestion_for_forecast_weather(processed_data_for_outfit_logic: dict) -> dict:
    """
    根據未來預報的已處理數據提供綜合穿搭建議。
    此函數只負責判斷建議文字和圖片，不進行數據解析和轉換。

    Args:
        processed_data_for_outfit_logic (dict): 包含以下已處理和聚合的數值型數據：
            - 'weather_phenomena': set, 包含天氣現象關鍵字 (如 '雨', '雷雨', '晴', '陰', '多雲')
            - 'max_feels_like_temp': int, 當天最高體感溫度
            - 'min_feels_like_temp': int, 當天最低體感溫度
            - 'temp_range_diff': int, 當天體感溫差
            - 'avg_humidity': int, 當天平均濕度
            - 'pop': int, 當天最高降雨機率
            - 'wind_speed': int, 當天最高風速 (蒲福風級)
            - 'comfort_max_desc': str, 白天或整體最高舒適度描述
            - 'comfort_min_desc': str, 夜間或整體最低舒適度描述
            - 'uvi': int, 當天最高紫外線指數
            
    Returns:
        dict: 包含 'suggestion_text' (list of str) 和 'suggestion_image_url' 的字典。
    """
    # 直接提取已處理的數據，這些數據已經在 forecast_flex_converter.py 中聚合和轉換完成
    weather_phenomena = processed_data_for_outfit_logic.get('weather_phenomena', set())
    max_feels_like_temp = processed_data_for_outfit_logic.get('max_feels_like_temp')
    min_feels_like_temp = processed_data_for_outfit_logic.get('min_feels_like_temp')
    temp_range_diff = processed_data_for_outfit_logic.get('temp_range_diff')
    avg_humidity = processed_data_for_outfit_logic.get('avg_humidity')
    pop = processed_data_for_outfit_logic.get('pop')
    wind_speed = processed_data_for_outfit_logic.get('wind_speed') # 這裡的 wind_speed 已經是蒲福風級

    comfort_max_desc = processed_data_for_outfit_logic.get('comfort_max_desc', '')
    comfort_min_desc = processed_data_for_outfit_logic.get('comfort_min_desc', '')
    uvi = processed_data_for_outfit_logic.get('uvi')

    # 檢查核心數據是否存在，如果沒有則返回預設值
    if any(val is None for val in [max_feels_like_temp, min_feels_like_temp, temp_range_diff, avg_humidity, pop, wind_speed, uvi]):
        logger.warning("未來預報穿搭建議所需的核心數據不完整。")
        return {"suggestion_text": ["未來天氣預報資料不足，無法提供詳細穿搭建議。"], "suggestion_image_url": IMAGE_URLS["NO_DATA"]}

    """
    if not forecast_data or not isinstance(forecast_data, list) or not forecast_data[0]:
        return {"suggestion_text": ["未來天氣預報資料不足或格式錯誤。"], "suggestion_image_url": "https://i.imgur.com/no_data.png"}
    
    # 取出單日數據（因為調用時是傳入 [day_data]）
    day_data = forecast_data[0]
    """

    # 初始化用於儲存建議的列表和預設圖片
    # suggestions_raw = [] # 儲存原始、詳細的建議
    final_suggestions = [] # 儲存最終精簡後的建議
    image_url = IMAGE_URLS["DEFAULT"] # 預設圖片

    # --- 穿搭建議邏輯 ---

    # 極端高溫
    if max_feels_like_temp >= 32:
        final_suggestions.append("• 預期天氣極度炎熱，體感悶熱，務必穿著最輕薄、透氣且吸濕排汗的衣物，如棉麻或機能性短袖、短褲或裙子。")
        image_url = IMAGE_URLS["HOT"]
    # 極端低溫
    elif min_feels_like_temp <= 12:
        final_suggestions.append("• 天氣偏冷，體感寒涼，外出請務必準備厚外套、毛衣或羽絨服，並注意頸部和四肢保暖。")
        image_url = IMAGE_URLS["COLD"]
    # 溫暖舒適區 (在極端溫度之後判斷，如果沒有極端溫度，則給出一般建議)
    elif 28 <= max_feels_like_temp < 32 and min_feels_like_temp >= 24: # 炎熱舒適區
        final_suggestions.append("• 白天炎熱，但整體體感舒適，建議穿著涼爽短袖，若進出冷氣房可備薄開衫。")
        image_url = IMAGE_URLS["WARM"] # 溫暖舒適圖
    # 涼爽舒適區
    elif 20 <= max_feels_like_temp < 28 and min_feels_like_temp >= 16: # 涼爽舒適區
        final_suggestions.append("• 天氣涼爽宜人，建議穿著薄長袖或搭配薄外套，早晚可能微涼。")
        image_url = IMAGE_URLS["COOL"] # 涼爽圖
    else: # 涵蓋其他溫和情況和較大溫差，給出一般舒適建議
        final_suggestions.append("• 氣溫適中，穿著舒適即可，建議採用洋蔥式穿搭以應對可能的氣溫變化。")
        image_url = IMAGE_URLS["COMFORTABLE"] # 舒適天氣圖

    # 2. 降雨建議 (僅添加文字，圖片處理在主邏輯中，或需要更精細的圖片優先級控制)
    # 注意：這裡的圖片邏輯需要調整，確保不會被後續覆蓋了最重要的降雨圖
    if pop is not None:
        if pop >= 70:
            final_suggestions.append("• 降雨機率極高，有大雨可能，外出務必攜帶堅固雨具，建議穿著防水外套和鞋子。")
            # 如果主要溫度建議沒有賦予更優先的圖片 (如極熱/極冷)，則覆蓋為重雨圖
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"]]:
                image_url = IMAGE_URLS["HEAVY_RAIN"] # 大雨圖
        elif pop >= 40:
            final_suggestions.append("• 降雨機率較高，建議隨身攜帶雨具備用，穿著易乾或防潑水材質的衣物。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"]]:
                image_url = IMAGE_URLS["RAINY_FORECAST"] # 中雨圖
        elif 0 < pop < 40 and ("雨" in weather_phenomena or "雷雨" in weather_phenomena):
            final_suggestions.append("• 局部地區可能有短暫陣雨，外出建議攜帶輕便雨具。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["LIGHT_RAIN"] # 小雨圖

    # 溫差建議（補充）
    if temp_range_diff >= 8: # 如果溫差大於等於8度，且已經有基礎建議
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，早晚注意保暖，建議攜帶外套。")
    elif temp_range_diff >= 5:
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，建議備薄外套。")

    # --- 補充建議 ---
    # 濕度
    if avg_humidity is not None:
        if avg_humidity >= 85: # 極高濕度
            final_suggestions.append("• 濕度極高，體感可能悶熱或濕冷，建議選擇極度透氣、吸濕排汗的輕薄衣物。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"], IMAGE_URLS["LIGHT_RAIN"]]:
                image_url = IMAGE_URLS["HIGH_HUMIDITY"] # 高濕度圖
        elif avg_humidity >= 70 and max_feels_like_temp is not None and max_feels_like_temp >= 25: # 較高濕度
            final_suggestions.append("• 濕度偏高且氣溫較高，體感可能較為悶熱，建議穿著寬鬆、透氣的衣物。")
        elif avg_humidity < 40: # 乾燥
            final_suggestions.append("• 空氣較為乾燥，注意肌膚保濕，可考慮攜帶護手霜或補水用品。")
            # 避免覆蓋低溫、雨天等重要圖片
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"], IMAGE_URLS["LIGHT_RAIN"]]:
                image_url = IMAGE_URLS["DRY_WEATHER"] # 乾燥天氣圖

    # 4. 風速判斷 (風寒效應或影響穿戴穩定性)
    if wind_speed is not None:
        if wind_speed >= 7 and (min_feels_like_temp is None or min_feels_like_temp < 20): # 疾風或更高，且氣溫偏涼
            final_suggestions.append(f"• 風力屬於 {wind_speed}，注意風寒效應，建議穿著防風外套，並固定帽子或髮型。")
            if min_feels_like_temp is not None and min_feels_like_temp < 15:
                final_suggestions.append("• 尤其注意頭部、頸部保暖。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["WINDY"] # 有風圖
        elif wind_speed >= 5 and (min_feels_like_temp is None or min_feels_like_temp < 25): # 清風或更高，且氣溫偏涼
            final_suggestions.append(f"• 風力屬於 {wind_speed}，體感溫度可能略低，可備一件薄防風外套。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["WINDY"]
        elif wind_speed >= 3 and (min_feels_like_temp is not None and min_feels_like_temp < 15): # 微風或更高，但氣溫較低
            final_suggestions.append(f"• 風力屬於 {wind_speed} 級，雖然風不大但天氣微涼，請注意保暖。")

    # 5. 紫外線指數判斷 (防曬提醒)
    if uvi is not None:
        if uvi >= 11: # 危險級
            final_suggestions.append(f"• 紫外線指數高達 {uvi}！戶外活動務必全程做好防曬，包括防曬乳、帽子、太陽眼鏡、遮陽傘，建議穿著長袖、輕薄透氣的衣物。")
            # 優先使用最高等級的UVI圖，但如果已經是極端天氣（冷、大雨），不覆蓋
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                 image_url = IMAGE_URLS["HIGH_UVI"] # 使用更強的HIGH_UVI圖片
        if uvi >= 8: # 極量或過量
            final_suggestions.append(f"• 紫外線指數高達 {uvi}！長時間戶外活動請加強防曬，建議戴太陽眼鏡、遮陽帽，塗抹防曬乳。")
            if max_feels_like_temp is not None and max_feels_like_temp >= 25: # 在炎熱天氣下，紫外線更需要強調防曬衣物
                final_suggestions.append("• 可考慮穿著防曬衣物。")
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["HIGH_UVI"] # 紫外線高圖
        elif uvi >= 6: # 中量或高量
            final_suggestions.append(f"• 紫外線指數為 {uvi}，外出建議戴太陽眼鏡、遮陽帽，並塗抹防曬乳。")
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"], IMAGE_URLS["HIGH_UVI"]]:
                image_url = IMAGE_URLS["HIGH_UVI"]
        elif uvi >= 3: # 中等
            final_suggestions.append(f"• 紫外線指數為 {uvi} 級 (中)，外出可戴太陽眼鏡。")
    else:
        final_suggestions.append("• 紫外線指數資訊不完整。")

    # 舒適度文字描述補充
    if comfort_max_desc is not None and comfort_min_desc is not None:
        if any(word in comfort_max_desc for word in ["悶熱", "不舒適", "炎熱"]) and not any("悶熱" in s or "炎熱" in s for s in final_suggestions):
            final_suggestions.append("• 體感偏向悶熱，請盡量減少衣物層次。")
        if any(word in comfort_min_desc for word in ["涼", "冷", "寒冷"]) and not any("寒涼" in s or "冷" in s for s in final_suggestions):
            final_suggestions.append("• 夜間或清晨可能感覺涼冷，注意身體末梢保暖。")

    # 確保至少有一條建議
    if not final_suggestions:
        final_suggestions.append("• 今日天氣狀況大致良好，穿著舒適即可。")
        if image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # 去重並合併建議
    final_suggestions = list(dict.fromkeys(final_suggestions)) # 利用字典的特性去重並保持順序

    # 確保圖片在多個條件下，選取最符合當前天氣狀況的圖片，可以設定優先級
    # 例如：下雨 > 低溫 > 高溫 > 高濕度 > 強風 > 紫外線高 > 舒適 > 默認
    # 為了簡化，這裡已經在邏輯判斷中直接賦值圖片，後續的條件會覆蓋之前的，達到某種優先級

    logger.debug(f"預報穿搭建議生成: {final_suggestions}, 圖: {image_url}")
    return {
        "suggestion_text": final_suggestions,
        "suggestion_image_url": image_url
    }
