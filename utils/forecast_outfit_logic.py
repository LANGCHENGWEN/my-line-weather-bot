# utils/forecast_outfit_logic.py
import logging

logger = logging.getLogger(__name__)

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
    suggestions = []
    image_url = "https://i.imgur.com/forecast_default.png" # 預設圖片

    # 從 day_data 中提取並轉換數值，考慮 'day' 和 'night' 兩個時段
    # 溫度
    min_temp_day = _to_int(day_data.get('min_temp_day', 999))
    min_temp_night = _to_int(day_data.get('min_temp_night', 999))
    max_temp_day = _to_int(day_data.get('max_temp_day', 0))
    max_temp_night = _to_int(day_data.get('max_temp_night', 0))
    
    # 獲取單日總體最高溫和最低溫
    min_temp = min(min_temp_day, min_temp_night) # 找出當天所有時段的最低溫
    max_temp = max(max_temp_day, max_temp_night) # 找出當天所有時段的最高溫

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

    # 天氣現象 (合併日夜的天氣現象)
    weather_phenomenon_day = day_data.get('weather_desc_day', '')
    weather_phenomenon_night = day_data.get('weather_desc_night', '')
    all_phenomena = []
    if weather_phenomenon_day:
        all_phenomena.extend([p.strip() for p in weather_phenomenon_day.split(',') if p.strip()])
    if weather_phenomenon_night:
        all_phenomena.extend([p.strip() for p in weather_phenomenon_night.split(',') if p.strip()])
    weather_phenomenon = ", ".join(list(set(all_phenomena))) # 去重後合併

    # 舒適度指數 (取日夜中極端的數值)
    # 注意: weather_forecast_parser 中 'comfort_max' 和 'comfort_min' 是 Description，而非數值
    # 你可能需要一個映射表將文字描述轉換為一個可比較的數值，或者直接用文字判斷
    # 這裡我們將其視為文字，並在邏輯中直接判斷文字
    comfort_max_desc = day_data.get('comfort_max_day', day_data.get('comfort_max_night', ''))
    comfort_min_desc = day_data.get('comfort_min_day', day_data.get('comfort_min_night', ''))

    # 紫外線指數 (取日夜中較高的 UVI)
    uvi_day = _to_int(day_data.get('uv_index_day', 0))
    uvi_night = _to_int(day_data.get('uv_index_night', 0))
    uvi = max(uvi_day, uvi_night)

    # --- 穿搭建議邏輯 ---

    # 1. 體感溫度判斷 (優先級較高)
    if max_feels_like_temp >= 32:
        suggestions.append("氣溫炎熱，體感悶熱。建議穿著輕薄、透氣、吸濕排汗的衣物，如棉麻短袖、短褲或裙子。")
        image_url = "https://i.imgur.com/hot_and_humid.png" # 高溫悶熱圖
    elif min_feels_like_temp <= 15:
        suggestions.append("氣溫偏低，體感寒冷。請務必準備保暖衣物，如厚外套、毛衣、圍巾等。")
        image_url = "https://i.imgur.com/cold_forecast.png" # 寒冷圖
    elif 25 <= max_feels_like_temp < 32 and min_feels_like_temp >= 20:
        suggestions.append("天氣舒適宜人。建議穿著薄長袖或短袖，早晚可搭配薄外套。")
        image_url = "https://i.imgur.com/comfortable_weather.png" # 舒適天氣圖
    else: # 默認溫差不大或中等
        suggestions.append("氣溫變化不大，體感大致舒適。建議根據室內外活動調整穿著。")
        if not any(url.endswith(img_suffix) for url, img_suffix in [("hot_and_humid.png", "hot_and_humid.png"), ("cold_forecast.png", "cold_forecast.png")]):
            image_url = "https://i.imgur.com/forecast_default.png" # 預設溫和天氣圖

    # 2. 降雨機率判斷 (更詳細)
    if pop >= 70:
        suggestions.append("降雨機率極高，外出務必攜帶雨具，建議穿著防水外套和鞋子。")
        image_url = "https://i.imgur.com/heavy_rain.png" # 大雨圖
    elif pop >= 40:
        suggestions.append("有較高降雨機率，建議攜帶雨具備用，穿著易乾的衣物。")
        if not image_url.endswith("heavy_rain.png"): # 如果不是大雨，就顯示中雨圖
            image_url = "https://i.imgur.com/rainy_forecast.png" # 中雨圖
    elif pop > 0 and pop < 40 and ("雨" in weather_phenomenon or "陣雨" in weather_phenomenon):
        suggestions.append("局部地區可能有短暫降雨，外出建議攜帶輕便雨具。")
        if not any(url.endswith(img_suffix) for url, img_suffix in [("heavy_rain.png", "heavy_rain.png"), ("rainy_forecast.png", "rainy_forecast.png")]):
             image_url = "https://i.imgur.com/light_rain.png" # 小雨圖

    # 3. 濕度判斷 (影響體感)
    if avg_humidity >= 80:
        suggestions.append("濕度較高，體感悶熱或濕冷。選擇透氣排汗的衣物，注意除濕。")
        if not any(url.endswith(img_suffix) for url, img_suffix in [("hot_and_humid.png", "hot_and_humid.png"), ("rainy_forecast.png", "rainy_forecast.png"), ("heavy_rain.png", "heavy_rain.png")]):
            image_url = "https://i.imgur.com/high_humidity.png" # 高濕度圖
    elif avg_humidity < 40:
        suggestions.append("濕度較低，空氣乾燥。注意保濕，可搭配薄圍巾或口罩。")
        if not image_url.endswith("cold_forecast.png"): # 避免覆蓋低溫圖
            image_url = "https://i.imgur.com/dry_weather.png" # 乾燥天氣圖

    # 4. 風速判斷
    if wind_speed >= 7: # 較強風 (約4級風以上)
        suggestions.append(f"風速較強 ({wind_speed}級風)，體感溫度會降低。建議穿著防風外套，並固定好帽子或髮型。")
        if not image_url.endswith("cold_forecast.png"): # 避免覆蓋低溫圖
            image_url = "https://i.imgur.com/windy_outfit.png" # 有風圖
    elif wind_speed >= 4: # 中等風 (約2-3級風)
        suggestions.append(f"風勢略強 ({wind_speed}級風)，穿著時考慮輕便防風。")

    # 5. 舒適度指數判斷 (基於文字描述)
    if "炎熱" in comfort_max_desc or "悶熱" in comfort_max_desc or "不舒適" in comfort_max_desc:
        suggestions.append("舒適度指數偏高，感覺炎熱或悶熱。盡量減少衣物層次。")
    if "涼" in comfort_min_desc or "冷" in comfort_min_desc or "寒冷" in comfort_min_desc:
        suggestions.append("舒適度指數偏低，感覺涼冷。注意身體末梢保暖。")

    # 6. 紫外線指數判斷
    if uvi >= 8: # 極量或過量
        suggestions.append("紫外線指數過高，外出務必做好防曬措施，如塗抹防曬乳、戴帽子、太陽眼鏡，並穿著薄長袖防曬衣物。")
        if not image_url.endswith("hot_and_humid.png"): # 避免覆蓋更重要的體感圖
            image_url = "https://i.imgur.com/high_uvi.png" # 紫外線高圖
    elif uvi >= 5: # 中量或高量
        suggestions.append("紫外線指數較高，建議做好基本防曬。")

    # 如果沒有特定建議，給出通用建議
    if not suggestions:
        suggestions.append("天氣狀況平穩，穿著舒適即可。")
        image_url = "https://i.imgur.com/forecast_default.png"

    # 去重並合併建議
    final_suggestions = list(dict.fromkeys(suggestions)) # 利用字典的特性去重並保持順序

    # 確保圖片在多個條件下，選取最符合當前天氣狀況的圖片，可以設定優先級
    # 例如：下雨 > 低溫 > 高溫 > 高濕度 > 強風 > 紫外線高 > 舒適 > 默認
    # 為了簡化，這裡已經在邏輯判斷中直接賦值圖片，後續的條件會覆蓋之前的，達到某種優先級

    logger.debug(f"預報穿搭建議生成: {final_suggestions}, 圖: {image_url}")
    return {"suggestion_text": final_suggestions, "suggestion_image_url": image_url}
