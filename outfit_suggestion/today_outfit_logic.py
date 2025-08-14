# outfit_suggestion/today_outfit_logic.py
"""
根據多個氣象數據來源，為用戶生成一個全面的「今日穿搭建議」。
整合了逐時預報、整體天氣概況和紫外線指數等資訊，並根據這些數據中的體感溫度、濕度、降雨機率、風速與紫外線指數等關鍵因子，動態產生穿搭文字建議和對應的圖片連結。
"""
import logging
from typing import Any, List, Dict

logger = logging.getLogger(__name__)

# --- 定義不同天氣情境所對應的圖片 URL ---
# 將圖片 URL 集中管理在一個字典中，可以讓程式碼更清晰，也方便日後的圖片更換或新增
# 函式可以直接透過鍵值 (key) 來存取對應的圖片，避免在邏輯判斷中硬編碼 URL
IMAGE_URLS = {
    "DEFAULT"       : "https://i.imgur.com/current_default.png",
    "HOT"           : "https://i.imgur.com/hot_weather_outfit.png",
    "WARM"          : "https://i.imgur.com/warm_weather_outfit.png",
    "COOL"          : "https://i.imgur.com/cool_weather_outfit.png",
    "CHILLY"        : "https://i.imgur.com/chilly_weather_outfit.png",
    "COLD"          : "https://i.imgur.com/cold_weather_outfit.png",
    "FREEZING"      : "https://i.imgur.com/freezing_weather_outfit.png",
    "HEAVY_RAIN"    : "https://i.imgur.com/heavy_rain.png",
    "LIGHT_RAIN"    : "https://i.imgur.com/light_rain.png",
    "RAINY_CURRENT" : "https://i.imgur.com/rainy_current.png",
    "WINDY"         : "https://i.imgur.com/windy_outfit.png",
    "HIGH_UVI"      : "https://i.imgur.com/high_uvi.png",
    "COMFORTABLE"   : "https://i.imgur.com/comfortable_weather.png"
}

def get_outfit_suggestion_for_today_weather(
    location: str,
    hourly_forecast: List[Dict[str, Any]],
    general_forecast: Dict[str, Any],
    uv_data: Dict[str, Any] | None
) -> Dict[str, Any]:
    """
    根據綜合天氣數據，為用戶生成每日穿搭建議。
    接收地點、逐時預報、整體天氣概況和紫外線指數等多種數據，依據這些資訊中的體感溫度、濕度、降雨機率、風速和紫外線指數，邏輯性的判斷並組合成一個包含多個層次的穿搭建議文本，並挑選出最能代表今日天氣狀況的圖片 URL。
    最後將所有相關數據打包成一個字典返回，供上層的 Flex Message 建立器使用。
    
    Args:
        general_forecast (dict): F-C0032-001 整體天氣狀況數據字典。
            'weather_phenomenon' (天氣現象，如晴、陰、雨)
            'max_temp_raw' (最高溫度，數值，用於判斷)
            'min_temp_raw' (最低溫度，數值，用於判斷)
            'formatted_temp_range' (組合的溫度區間顯示字串)
            'pop_raw' (降雨機率，數值，用於判斷)
            'pop_formatted' (組合的降雨機率顯示字串)
        hourly_forecast (list): F-D0047-089 逐小時天氣數據列表。
            'apparent_temp_raw' (體感溫度，數值，用於判斷)
            'apparent_temp_formatted' (組合的體感溫度顯示字串)
            'humidity_raw' (濕度，數值，用於判斷)
            'wind_scale_raw' (蒲福風級數字，用於判斷)
            'wind_scale_formatted' (組合的蒲福風級顯示字串)
        uv_data (dict): O-A0005-001 紫外線指數數據字典。
            'UVIndexRaw' (紫外線指數，數值，用於判斷)
            'UVIndexFormatted' (組合的紫外線指數顯示字串)

    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """
    logger.debug(f"[OutfitLogic] 正在為 {location} 產生穿搭建議。")

    # --- 從 general_forecast (F-C0032-001) 提取數據 ---
    # 確保這裡使用的鍵名與 weather_today_parser.py 的輸出一致
    date_full_formatted = general_forecast.get("date_full_formatted")
    weather_phenomenon = general_forecast.get("weather_phenomenon")

    # 獲取原始數值，用於判斷
    max_temp_raw = general_forecast.get("max_temp_raw", None)
    min_temp_raw = general_forecast.get("min_temp_raw", None) 
    precipitation_prob_raw = general_forecast.get("pop_raw", None)

    # 已經格式化好、直接用於顯示 Flex Message 的字串，來自解析器
    formatted_temp_range = general_forecast.get("formatted_temp_range") # 從解析器直接獲取帶 °C 的字串
    formatted_pop = general_forecast.get("pop_formatted") # 從解析器直接獲取帶 % 的字串

    logger.debug(f"成功提取今日天氣數據: 溫度: {formatted_temp_range}, 降雨: {formatted_pop}")

    # --- 從 hourly_forecast (F-D0047-089) 獲取當前或最近的逐時預報數據 ---
    # 確保這裡使用的鍵名與 weather_3days_parser.py 的輸出一致
    current_hour_data = hourly_forecast[0] if hourly_forecast else None # 取出目前或最近一個小時的天氣預報資料

    if current_hour_data:
        # 獲取原始數值，用於判斷
        apparent_temp_raw = current_hour_data.get("apparent_temp_raw")
        humidity_raw = current_hour_data.get("humidity_raw")

        # 從解析器直接獲取帶 °C 的字串
        formatted_feels_like = current_hour_data.get("apparent_temp_formatted")
        
        # 獲取格式化後的純數字蒲福風級和描述字串
        wind_scale_raw = current_hour_data.get("wind_scale_raw") # 純數字的蒲福風級，用於判斷
        formatted_wind_scale = current_hour_data.get("wind_scale_formatted") # 這是 "X 級 (描述)" 的字串
        
        logger.debug(f"成功提取逐時數據: 體感: {formatted_feels_like}, 風速: {formatted_wind_scale}")
    else:
        logger.warning(f"未能找到 {location} 可用的逐時天氣預報數據，體感溫度、風速將為無資料。")

    # --- 從 uv_data (O-A0005-001) 獲取紫外線指數 ---
    # 確保這裡使用的鍵名與 today_uvindex_parser.py 的輸出一致
    uv_index_raw_val = uv_data.get("UVIndexRaw", None) # 獲取原始數值，用於判斷
    uv_index_formatted_str = uv_data.get("UVIndexFormatted", "無資料") # 組合後的顯示字串

    if uv_index_formatted_str == "無資料":
        logger.warning("未接收到有效的紫外線指數資訊。")
    else:
        logger.info(f"成功接收格式化紫外線指數: {uv_index_formatted_str}")

    # --- 生成穿搭建議文本 ---
    """
    根據不同的溫度區間（例如「炎熱」、「溫暖」、「寒冷」），函式會給出一個基礎的穿搭建議，並同時選擇一張對應的圖片。
    獨立的根據降雨機率、風速和紫外線指數來添加額外的建議，這種方式讓不同的天氣因素可以獨立影響最終的建議，而不是互相覆蓋。
    """
    suggestion_text = [] # 使用列表儲存建議的各部分，方便後面組裝
    suggestion_image_url = IMAGE_URLS["DEFAULT"] # 預設圖
    
    # --- 根據體感溫度給出基礎穿搭建議 ---
    if apparent_temp_raw is not None:
        # 添加濕度判斷的輔助變數或直接判斷
        is_high_humidity = humidity_raw is not None and humidity_raw >= 75 # 高濕度定義為 75% 以上
        is_low_humidity = humidity_raw is not None and humidity_raw <= 40 # 低濕度定義為 40% 以下

        if apparent_temp_raw >= 32:
            base_suggestion = "• 天氣非常炎熱，請穿著輕薄、透氣的棉麻衣物，建議短袖、短褲或裙裝，務必注意防曬並多補充水分，避免中暑！"
            if is_high_humidity:
                base_suggestion = "• 天氣非常炎熱且潮濕悶熱，請穿著極度輕薄、吸濕排汗的棉麻或機能性衣物，建議短袖、短褲或裙裝，務必注意防曬並多補充水分，避免中暑！"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["HOT"]
        elif 28 <= apparent_temp_raw < 32:
            base_suggestion = "• 天氣炎熱，建議穿著短袖或薄長袖，搭配短褲或輕薄長褲/裙裝，外出請攜帶遮陽帽或陽傘。"
            if is_high_humidity:
                base_suggestion = "• 天氣炎熱且濕度較高，建議穿著透氣排汗的短袖或薄長袖，搭配短褲或輕薄長褲/裙裝，外出請攜帶遮陽帽或陽傘，避免悶熱不適。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["HOT"]
        elif 24 <= apparent_temp_raw < 28:
            base_suggestion = "• 天氣溫暖舒適，可穿著短袖或薄長袖，早晚溫差可能稍大，建議攜帶一件薄外套以備不時之需。"
            if is_high_humidity:
                base_suggestion = "• 天氣溫暖舒適但濕度稍高，可穿著短袖或薄長袖（選擇透氣材質），早晚溫差可能稍大，建議攜帶一件薄外套以備不時之需。"
            elif is_low_humidity:
                base_suggestion = "• 天氣溫暖舒適且乾燥，可穿著短袖或薄長袖，早晚溫差可能稍大，建議攜帶一件薄外套，並注意皮膚保濕。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["WARM"]
        elif 19 <= apparent_temp_raw < 24:
            base_suggestion = "• 天氣涼爽，建議穿著長袖上衣，搭配輕薄外套或針織衫，早晚氣溫較低，注意保暖。"
            if is_high_humidity:
                base_suggestion = "• 天氣涼爽且濕度較高，建議穿著長袖上衣，搭配防潮或輕薄透氣外套或針織衫，早晚氣溫較低，注意保暖。"
            elif is_low_humidity:
                base_suggestion = "• 天氣涼爽且乾燥，建議穿著長袖上衣，搭配輕薄外套或針織衫，早晚氣溫較低，注意保暖，並可加強皮膚與唇部保濕。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["COOL"]
        elif 14 <= apparent_temp_raw < 19:
            base_suggestion = "• 天氣偏涼，請注意保暖！建議穿著厚長袖、薄毛衣或搭配中等厚度的外套。"
            if is_high_humidity:
                base_suggestion = "• 天氣偏涼且濕度較高，請注意保暖！建議穿著厚長袖、薄毛衣或搭配防風防潮的中等厚度外套，避免濕冷感。"
            elif is_low_humidity:
                base_suggestion = "• 天氣偏涼且乾燥，請注意保暖！建議穿著厚長袖、薄毛衣或搭配中等厚度的外套，可準備保濕乳液。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["CHILLY"]
        elif 10 <= apparent_temp_raw < 14:
            base_suggestion = "• 天氣寒冷，請穿著厚外套、毛衣，務必注意保暖。"
            if is_high_humidity:
                base_suggestion = "• 天氣寒冷且濕度較高，體感濕冷，請穿著厚外套、毛衣，務必注意保暖，選擇有防風或防潑水功能的外套更佳。"
            elif is_low_humidity:
                base_suggestion = "• 天氣寒冷且乾燥，請穿著厚外套、毛衣，務必注意保暖，並可加強保濕，避免皮膚乾裂。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["COLD"]
        else:
            base_suggestion = "• 天氣非常寒冷，務必做好保暖！建議穿著厚毛衣、羽絨服或保暖大衣，並搭配圍巾、手套等配件。"
            if is_high_humidity:
                base_suggestion = "• 天氣非常寒冷且濕度極高，體感非常濕冷，務必做好保暖！建議穿著厚毛衣、具備防水防風功能的羽絨服或保暖大衣，並搭配圍巾、手套等配件，避免寒氣入侵。"
            elif is_low_humidity:
                base_suggestion = "• 天氣非常寒冷且乾燥，務必做好保暖！建議穿著厚毛衣、羽絨服或保暖大衣，並搭配圍巾、手套等配件，同時注意全身的保濕。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["FREEZING"]
    else:
        # 備用方案：如果體感溫度數據不可用，則退而求其次，使用最高/最低氣溫的平均值來進行概略判斷
        if min_temp_raw is not None and max_temp_raw is not None:
            avg_temp = (min_temp_raw + max_temp_raw) / 2
            if avg_temp >= 28:
                suggestion_text.append("• 氣溫炎熱，請選擇輕薄透氣衣物。")
                suggestion_image_url = IMAGE_URLS["HOT"]
            elif 22 <= avg_temp < 28:
                suggestion_text.append("• 氣溫舒適，早晚可能微涼，建議備薄外套。")
                suggestion_image_url = IMAGE_URLS["WARM"]
            else:
                suggestion_text.append("• 氣溫偏涼，請注意保暖。")
                suggestion_image_url = IMAGE_URLS["CHILLY"]
        else:
            suggestion_text.append("• 目前無法根據溫度提供詳細穿搭建議，請自行參考其他天氣資訊判斷。")

    # --- 針對降雨情況進行補充 ---
    """
    在已經有基礎溫度建議的情況下，疊加更具體的降雨應對措施。
    檢查 `weather_phenomenon` 描述和原始的 `precipitation_prob_raw` 數字，根據不同的降雨強度（豪雨、陣雨、雷陣雨）來追加不同的建議。
    """
    if "豪雨" in weather_phenomenon or "大雨" in weather_phenomenon or (precipitation_prob_raw is not None and precipitation_prob_raw > 50):
        suggestion_text.append("• 降雨機率極高，外出務必攜帶雨具，建議穿著防水性佳的衣物及鞋子。")
        suggestion_image_url = IMAGE_URLS["HEAVY_RAIN"]
    elif "午後雷陣雨" in weather_phenomenon:
        suggestion_text.append("• 午後有雷陣雨，外出請攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["LIGHT_RAIN"]
    elif "陣雨" in weather_phenomenon or "雷雨" in weather_phenomenon or "雨" in weather_phenomenon:
        if precipitation_prob_raw is not None and 0 < precipitation_prob_raw <= 50:
            suggestion_text.append("• 降雨機率較高，建議攜帶雨具，穿著防潑水衣物或備薄外套。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]
        elif precipitation_prob_raw is not None and precipitation_prob_raw == 0 and ("陣雨" in weather_phenomenon or "雨" in weather_phenomenon):
            # 天氣描述有雨但降雨機率為 0，可能是短暫或預期有雨但尚未發生
            suggestion_text.append("• 可能有短暫降雨，建議攜帶雨具。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]

    # --- 補充風速/風寒建議 (使用蒲福風級數字判斷和描述) ---
    """
    根據風力等級來調整穿搭建議。
    風寒效應會讓體感溫度比實際氣溫更低，因此在風力較大的情況下，僅依賴體感溫度可能不足。
    檢查原始的風力等級 (`wind_scale_raw`)，如果風力強勁，就會追加提醒防風保暖的建議，並可能替換掉原本的圖片。
    """
    if wind_scale_raw is not None and apparent_temp_raw is not None:
        if wind_scale_raw >= 7: # 強風以上 (7級或更高)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，風寒效應顯著，請特別注意防風保暖，務必穿著防風外套，並加強頭頸部保暖。")
            if apparent_temp_raw < 15:
                suggestion_text.append("• 尤其注意頭部、頸部保暖。")
            suggestion_image_url = IMAGE_URLS["WINDY"]
        elif wind_scale_raw >= 5: # 和風到勁風 (5-6級)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，體感溫度可能略低，建議可備一件薄防風外套。")
            suggestion_image_url = IMAGE_URLS["WINDY"]
        elif wind_scale_raw >= 3: # 微風 (3級)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，體感略受影響，一般輕薄外套足以應對。")
        else: # 0-2級，微風以下
            suggestion_text.append("• 今日風力較弱，穿搭上無需特別考慮風速影響。")

    # --- 補充紫外線指數建議 ---
    """
    針對紫外線指數的高低，提供具體的防曬建議。
    根據原始的紫外線指數數值，判斷危險等級（危險、過量、高），並在建議列表中添加相應的防曬措施，然後在適當情況下替換圖片。
    """
    if uv_index_raw_val is not None: # 使用原始數值進行判斷
        if uv_index_raw_val >= 11: # 危險
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_formatted_str}！戶外活動務必全程做好防曬，包括防曬乳、帽子、太陽眼鏡、遮陽傘。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["HOT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index_raw_val >= 8: # 過量
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_formatted_str}！長時間戶外活動請加強防曬，建議戴太陽眼鏡、遮陽帽，塗抹防曬乳。")
            if apparent_temp_raw is not None and apparent_temp_raw >= 25: # 在炎熱天氣下，紫外線更需要強調防曬衣物
                suggestion_text.append("• 可考慮穿著防曬衣物。")
            suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index_raw_val >= 6: # 高
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}，外出建議戴太陽眼鏡、遮陽帽，並塗抹防曬乳。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index_raw_val >= 3: # 中
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}，外出可戴太陽眼鏡。")
        else: # 低
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}。")
    else:
        suggestion_text.append("• 紫外線指數資訊不完整。")

    # --- 如果沒有特定建議，給出預設文字 ---
    # 這是一個最終的 fallback 邏輯，確保即使所有天氣數據都缺失，用戶也能收到一個預設的訊息
    if not suggestion_text:
        suggestion_text.append("• 今天天氣狀況良好，穿著舒適即可。")
        if suggestion_image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            suggestion_image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # --- 構造最終返回給 Flex Message 的數據字典 ---
    """
    將所有處理好的數據打包成一個字典，作為函式的最終回傳值。
    將所有的穿搭建議文本、圖片 URL 以及其他重要的天氣資訊組織在一起，形成一個統一的資料結構，這樣上層的 Flex Message 建立器只需要接收一個字典，就可以輕鬆的提取所需的資訊，並將其填入到訊息模板中，實現前後端邏輯的解耦。
    """
    outfit_info_to_return = {
        "outfit_suggestion_text": suggestion_text,
        "suggestion_image_url": suggestion_image_url,
        "date_full_formatted": date_full_formatted,
        "weather_phenomenon": weather_phenomenon,
        "feels_like": formatted_feels_like,           # 使用已格式化的字串
        "formatted_temp_range": formatted_temp_range, # 使用已格式化的字串
        "pop": formatted_pop,                         # 使用已格式化的字串
        "wind_scale": formatted_wind_scale,           # 使用蒲福風級顯示字串
        "uv_index": uv_index_formatted_str            # 使用已格式化的字串
    }

    logger.debug(f"今日穿搭建議生成及數據回傳: {outfit_info_to_return}")
    return outfit_info_to_return