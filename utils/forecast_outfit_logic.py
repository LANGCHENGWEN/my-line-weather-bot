# utils/forecast_outfit_logic.py
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

# 輔助函數：安全地將值轉換為數字
def _to_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

"""
def _to_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default
"""

def get_outfit_suggestion_for_forecast_weather(forecast_data: list) -> dict:
    """
    根據未來預報數據提供綜合穿搭建議。
    Args:
        forecast_data (list): 未來幾天的預報數據列表，實際上此函數會接收
                              一個包含單日數據的列表，該單日數據來自
                              weather_forecast_parser.py 的 'forecast_periods' 元素。
                              例如：[{'date': '2025-07-23', 'min_temp_day': '25', ...}]
    Returns:
        dict: 包含 'suggestion_text' (list of str) 和 'suggestion_image_url' 的字典。
    """
    if not forecast_data or not isinstance(forecast_data, list) or not forecast_data[0]:
        return {"suggestion_text": ["未來天氣預報資料不足或格式錯誤。"], "suggestion_image_url": "https://i.imgur.com/no_data.png"}
    
    # 取出單日數據（因為調用時是傳入 [day_data]）
    day_data = forecast_data[0]

    # 初始化用於儲存建議的列表和預設圖片
    suggestions_raw = [] # 儲存原始、詳細的建議
    final_suggestions = [] # 儲存最終精簡後的建議
    image_url = IMAGE_URLS["DEFAULT"] # 預設圖片

    # 從 day_data 中提取並轉換數值，考慮 'day' 和 'night' 兩個時段
    # 溫度
    min_temp_day = _to_int(day_data.get('min_temp_day', 999))
    min_temp_night = _to_int(day_data.get('min_temp_night', 999))
    max_temp_day = _to_int(day_data.get('max_temp_day', 0))
    max_temp_night = _to_int(day_data.get('max_temp_night', 0))
    
    # 獲取單日總體最高溫和最低溫
    # min_temp = min(min_temp_day, min_temp_night) # 找出當天所有時段的最低溫
    # max_temp = max(max_temp_day, max_temp_night) # 找出當天所有時段的最高溫

    # 體感溫度 (取該日所有時段的最低和最高體感溫度)
    min_feels_like_temp_day = _to_int(day_data.get('min_feel_day', min_temp_day))
    min_feels_like_temp_night = _to_int(day_data.get('min_feel_night', min_temp_night))
    max_feels_like_temp_day = _to_int(day_data.get('max_feel_day', max_temp_day))
    max_feels_like_temp_night = _to_int(day_data.get('max_feel_night', max_temp_night))

    min_feels_like_temp = min(min_feels_like_temp_day, min_feels_like_temp_night)
    max_feels_like_temp = max(max_feels_like_temp_day, max_feels_like_temp_night)

    # 降雨機率 (取日夜中較高的 PoP)
    pop_day = _to_int(day_data.get('pop_day', 0))
    pop_night = _to_int(day_data.get('pop_night', 0))
    pop = max(pop_day, pop_night)

    # 平均相對濕度 (如果日夜都有，取平均或較高值。這裡先取白天的為準，或可考慮平均)
    avg_humidity = _to_int(day_data.get('humidity_day', day_data.get('humidity_night', 0))) # 優先取白天，否則取晚上

    # 風速 (取日夜中較高的風速)
    wind_speed_day = _to_int(day_data.get('wind_speed_day', 0))
    wind_speed_night = _to_int(day_data.get('wind_speed_night', 0))
    wind_speed = max(wind_speed_day, wind_speed_night)

    # 紫外線指數 (取日夜中較高的 UVI)
    uvi_day = _to_int(day_data.get('uv_index_day', 0))
    uvi_night = _to_int(day_data.get('uv_index_night', 0))
    uvi = max(uvi_day, uvi_night)

    # 天氣現象判斷，集合化，方便擴展
    weather_phenomenon_day = day_data.get('weather_desc_day', '')
    weather_phenomenon_night = day_data.get('weather_desc_night', '')
    weather_phenomena = set()
    for desc in [weather_phenomenon_day, weather_phenomenon_night]:
        if desc:
            parts = [p.strip() for p in desc.split(',')]
            for p in parts:
                if "雨" in p:
                    weather_phenomena.add("雨")
                if "雷" in p:
                    weather_phenomena.add("雷雨")
                if "晴" in p:
                    weather_phenomena.add("晴")
                if "陰" in p:
                    weather_phenomena.add("陰")
                if "多雲" in p:
                    weather_phenomena.add("多雲")

    # 舒適度指數 (取日夜中極端的數值)
    # 注意: weather_forecast_parser 中 'comfort_max' 和 'comfort_min' 是 Description，而非數值
    # 你可能需要一個映射表將文字描述轉換為一個可比較的數值，或者直接用文字判斷
    # 這裡我們將其視為文字，並在邏輯中直接判斷文字
    comfort_max_desc = day_data.get('comfort_max_day', day_data.get('comfort_max_night', ''))
    comfort_min_desc = day_data.get('comfort_min_day', day_data.get('comfort_min_night', ''))

    # --- 穿搭建議邏輯 ---
    # --- 主建議判斷 ---
    main_suggestion_made = False
    rain_suggestion_added = False

    if max_feels_like_temp is not None and min_feels_like_temp is not None:
        # 極端高溫
        if max_feels_like_temp >= 32:
            suggestions_raw.append("預期天氣極度炎熱，體感悶熱，務必穿著最輕薄、透氣且吸濕排汗的衣物，如棉麻或機能性短袖、短褲或裙子。")
            image_url = IMAGE_URLS["HOT"]
            main_suggestion_made = True
        # 極端低溫
        elif min_feels_like_temp <= 12:
            suggestions_raw.append("天氣偏冷，體感寒涼，外出請務必準備厚外套、毛衣或羽絨服，並注意頸部和四肢保暖。")
            image_url = IMAGE_URLS["COLD"]
            main_suggestion_made = True

    # 降雨建議（優先於一般建議，但不覆蓋極端溫度圖）
    # 將 pop 的判斷放在體感之後，但優先於其他輔助判斷，因為下雨對穿搭影響巨大
    if pop is not None:
        if pop >= 70:
            # 如果已經是極度炎熱/寒冷圖，優先維持其，否則用重雨圖
            if not main_suggestion_made:
                image_url = IMAGE_URLS["HEAVY_RAIN"] # 大雨圖
            suggestions_raw.append("降雨機率極高，有大雨可能，外出務必攜帶堅固雨具，建議穿著防水外套和鞋子。")
            rain_suggestion_added = True
        elif pop >= 40:
            if not main_suggestion_made and not rain_suggestion_added:
                image_url = IMAGE_URLS["RAINY_FORECAST"] # 中雨圖
            suggestions_raw.append("有較高降雨機率，建議隨身攜帶雨具備用，穿著易乾或防潑水材質的衣物。")
            rain_suggestion_added = True
        elif 0 < pop < 40 and ("雨" in weather_phenomena or "雷雨" in weather_phenomena):
            if not main_suggestion_made and not rain_suggestion_added:
                image_url = IMAGE_URLS["LIGHT_RAIN"] # 小雨圖
            suggestions_raw.append("局部地區可能有短暫陣雨，外出建議攜帶輕便雨具。")
            rain_suggestion_added = True

    # 溫差建議（補充）
    temp_range_diff = max_feels_like_temp - min_feels_like_temp
    if temp_range_diff >= 8: # 如果溫差大於等於8度，且已經有基礎建議
        suggestions_raw.append(f"日夜溫差約 {temp_range_diff}°C，早晚注意保暖，建議攜帶外套。")
    elif temp_range_diff >= 5:
        suggestions_raw.append(f"日夜溫差約 {temp_range_diff}°C，建議備薄外套。")

    # --- 補充建議 ---
    # 濕度
    if avg_humidity is not None:
        if avg_humidity >= 85: # 極高濕度
            suggestions_raw.append("濕度極高，體感可能悶熱或濕冷，建議選擇極度透氣、吸濕排汗的輕薄衣物。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"]]:
                image_url = IMAGE_URLS["HIGH_HUMIDITY"] # 高濕度圖
        elif avg_humidity >= 70: # 較高濕度
            if max_feels_like_temp is not None and max_feels_like_temp >= 25:
                suggestions_raw.append("濕度偏高且氣溫較高，體感可能較為悶熱，建議穿著寬鬆、透氣的衣物。")
            else:
                suggestions_raw.append("濕度偏高，空氣較為潮濕，注意衣物選擇透氣性。")
        elif avg_humidity < 40: # 乾燥
            suggestions_raw.append("空氣較為乾燥，注意肌膚保濕，可考慮攜帶護手霜或補水用品。")
            # 避免覆蓋低溫、雨天等重要圖片
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["DRY_WEATHER"] # 乾燥天氣圖

    # 4. 風速判斷 (風寒效應或影響穿戴穩定性)
    if wind_speed is not None:
        if wind_speed >= 7: # 較強風 (約4級風以上)
            suggestions_raw.append(f"風速較強 (約{wind_speed}級風)，注意風寒效應，建議穿著防風外套，並固定帽子或髮型。")
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["WINDY"] # 有風圖
        elif wind_speed >= 4: # 中等風 (約2-3級風)
            suggestions_raw.append(f"風勢略強 (約{wind_speed}級風)，體感微涼，可備輕便防風外套。")

    # 5. 紫外線指數判斷 (防曬提醒)
    if uvi is not None:
        if uvi >= 8: # 極量或過量
            suggestions_raw.append("紫外線極高，外出務必嚴格防曬，建議塗抹高係數防曬乳、戴帽子、太陽眼鏡，並穿著薄長袖防曬衣物，盡量避免長時間曝曬。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["HEAVY_RAIN"]]:
                image_url = IMAGE_URLS["HIGH_UVI"] # 紫外線高圖
        elif uvi >= 5: # 中量或高量
            suggestions_raw.append("紫外線較高，外出建議做好基礎防曬，如戴帽子或擦防曬乳。")
        elif uvi >= 3: # 中等
            suggestions_raw.append("紫外線中等，可進行基本防曬措施。")

    # 舒適度文字描述補充
    if comfort_max_desc is not None and comfort_min_desc is not None:
        if any(word in comfort_max_desc for word in ["悶熱", "不舒適", "炎熱"]) and not any("悶熱" in s or "炎熱" in s for s in suggestions_raw):
            suggestions_raw.append("體感偏向悶熱，請盡量減少衣物層次。")
        if any(word in comfort_min_desc for word in ["涼", "冷", "寒冷"]) and not any("寒涼" in s or "冷" in s for s in suggestions_raw):
            suggestions_raw.append("夜間或清晨可能感覺涼冷，注意身體末梢保暖。")

    # 主要溫度/舒適建議
    if main_suggestion_made: # 如果已經有極端溫度建議，直接使用
        if "炎熱" in suggestions_raw[0]: # 假設極度炎熱是第一個
            final_suggestions.append("• 預期極度炎熱，請穿著最輕薄透氣、吸濕排汗衣物(短袖、短褲/裙)。")
        elif "偏冷" in suggestions_raw[0]: # 假設極度寒冷是第一個
            final_suggestions.append("• 預期偏冷，務必準備厚外套、毛衣或羽絨服，並注意保暖。")
    elif not rain_suggestion_added: # 如果沒有極端溫度且沒有降雨建議，則給出一般舒適建議
        if 28 <= max_feels_like_temp < 32 and min_feels_like_temp >= 24: # 炎熱舒適區
            final_suggestions.append("• 白天炎熱，但整體體感舒適，建議穿著涼爽短袖，若進出冷氣房可備薄開衫。")
            image_url = IMAGE_URLS["WARM"] # 溫暖舒適圖
        elif 20 <= max_feels_like_temp < 28 and min_feels_like_temp >= 16: # 涼爽舒適區
            final_suggestions.append("• 天氣涼爽宜人，建議穿著薄長袖或搭配薄外套，早晚可能微涼。")
            image_url = IMAGE_URLS["COOL"] # 涼爽圖
        else: # 涵蓋其他溫和情況和較大溫差
            final_suggestions.append("• 氣溫適中，穿著舒適即可，建議採用洋蔥式穿搭以應對可能的氣溫變化。")
            image_url = IMAGE_URLS["COMFORTABLE"] # 舒適天氣圖

    # 降雨建議 (獨立優先級，但不重複主建議圖)
    if rain_suggestion_added:
        if pop >= 70:
            final_suggestions.append("• 降雨機率極高，可能大雨，務必攜帶堅固雨具，穿著防水外套、鞋子。")
        elif pop >= 40:
            final_suggestions.append("• 降雨機率較高，建議攜帶雨具，穿著易乾或防潑水衣物。")
        elif 0 < pop < 40 and ("雨" in weather_phenomena or "雷雨" in weather_phenomena):
            final_suggestions.append("• 局部短暫陣雨，建議攜帶輕便雨具。")

    # 溫差建議 (補充)
    if temp_range_diff >= 8:
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，早出晚歸務必攜帶外套。")
    elif temp_range_diff >= 5:
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，建議備薄外套。")

    # 濕度/體感悶熱 (補充)
    if avg_humidity is not None and avg_humidity >= 70 and max_feels_like_temp is not None and max_feels_like_temp >= 25:
        final_suggestions.append("• 濕度偏高，體感可能悶熱，建議穿著寬鬆透氣衣物。")
    elif avg_humidity is not None and avg_humidity >= 85: # 極高濕度且可能濕冷
        final_suggestions.append("• 濕度極高，體感可能悶熱或濕冷，選擇吸濕排汗輕薄衣物。")
    elif avg_humidity is not None and avg_humidity < 40:
        final_suggestions.append("• 空氣乾燥，注意肌膚和身體保濕。")


    # 風速 (補充)
    if wind_speed is not None:
        if wind_speed >= 7:
            final_suggestions.append(f"• 風速較強 ({wind_speed}級)，注意風寒效應，建議穿著防風外套。")
        elif wind_speed >= 4:
            final_suggestions.append(f"• 風勢略強 ({wind_speed}級)，體感微涼，可備輕便防風外套。")

    # 紫外線指數 (補充)
    if uvi is not None:
        if uvi >= 8:
            final_suggestions.append("• 紫外線極高，務必嚴格防曬。")
        elif uvi >= 5:
            final_suggestions.append("• 紫外線較高，建議做好基礎防曬。")

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
        "suggestion_text": final_suggestions, "suggestion_image_url": image_url
    }
