# outfit_suggestion/forecast_outfit_logic.py
"""
根據未來幾天的天氣預報數據，生成相應的穿搭建議文字和圖片。
接收已經過處理、聚合的數值型天氣數據（如最高/最低體感溫度、降雨機率、風速等），並基於這些數據進行綜合判斷，提供精確的穿搭建議。
這個模組只專注於「穿搭邏輯」本身，與數據的獲取及訊息的格式化完全分離，這種設計模式讓程式碼易於測試、維護和擴展。
"""
import logging

logger = logging.getLogger(__name__)

# --- 定義不同天氣情境所對應的圖片 URL ---
# 將圖片 URL 集中管理在一個字典中，可以讓程式碼更清晰，也方便日後的圖片更換或新增
# 函式可以直接透過鍵值 (key) 來存取對應的圖片，避免在邏輯判斷中硬編碼 URL
IMAGE_URLS = {
    "NO_DATA"        : "https://i.postimg.cc/T3qs1kMf/NO-DATA.png",
    "DEFAULT"        : "https://i.postimg.cc/N05xtLpR/DEFAULT.png",
    "HOT"            : "https://i.postimg.cc/43qQxZ0k/HOT.png",
    "COLD"           : "https://i.postimg.cc/yNkTKWvM/COLD.png",
    "WARM"           : "https://i.postimg.cc/mrJygR5J/WARM.png",
    "COOL"           : "https://i.postimg.cc/N0SkjYzn/COOL.png",
    "COMFORTABLE"    : "https://i.postimg.cc/HLVtmjB5/COMFORTABLE.png",
    "HEAVY_RAIN"     : "https://i.postimg.cc/6QyhKTYj/HEAVY_RAIN.png",
    "RAINY_FORECAST" : "https://i.postimg.cc/65WjS6JF/RAINY.png",
    "LIGHT_RAIN"     : "https://i.postimg.cc/s2vJz1wn/LIGHT_RAIN.png",
    "HIGH_HUMIDITY"  : "https://i.postimg.cc/LsnVShND/HIGH_HUMIDITY.png",
    "DRY_WEATHER"    : "https://i.postimg.cc/xdcPQqtR/DRY_WEATHER.png",
    "WINDY"          : "https://i.postimg.cc/tgYzb72d/WINDY.png",
    "HIGH_UVI"       : "https://i.postimg.cc/cLDcPfMX/HIGH_UVI.png"
}

def get_outfit_suggestion_for_forecast_weather(processed_data_for_outfit_logic: dict) -> dict:
    """
    根據未來預報的已處理和聚合的數據提供綜合穿搭建議。
    將多種天氣因素（如溫度、降雨、濕度、風速、紫外線等）結合起來，產生一套精準、多面向的穿搭文字建議，並選擇一張最能代表當天情境的圖片。
    此函式只負責判斷穿搭建議文字和圖片，不進行數據解析和轉換。
    
    Args:
        processed_data_for_outfit_logic (dict):
            'weather_phenomena' (天氣現象，如晴、陰、雨，集合)
            'max_feels_like_temp' (當天最高體感溫度，數值)
            'min_feels_like_temp' (當天最低體感溫度，數值)
            'temp_range_diff' (當天體感溫差，數值)
            'avg_humidity' (當天平均濕度，數值)
            'pop' (當天最高降雨機率，數值)
            'wind_speed' (當天最高風速 (蒲福風級)，數值)
            'comfort_max_desc' (白天或整體最高舒適度描述，字串)
            'comfort_min_desc' (夜間或整體最低舒適度描述，字串)
            'uvi' (當天最高紫外線指數，數值)

    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """

    # --- 從傳入的字典中，安全的提取所有用於判斷穿搭建議的數據 ---
    # 這些數據在傳入此函式之前，已經由 forecast_flex_converter.py 進行了聚合和轉換
    # 直接使用已處理的數據，專注於判斷邏輯，而不是重複進行數據處理，這符合單一職責原則
    weather_phenomena = processed_data_for_outfit_logic.get('weather_phenomena', set())
    max_feels_like_temp = processed_data_for_outfit_logic.get('max_feels_like_temp')
    min_feels_like_temp = processed_data_for_outfit_logic.get('min_feels_like_temp')
    temp_range_diff = processed_data_for_outfit_logic.get('temp_range_diff')
    avg_humidity = processed_data_for_outfit_logic.get('avg_humidity')
    pop = processed_data_for_outfit_logic.get('pop')
    wind_speed = processed_data_for_outfit_logic.get('wind_speed') # 這裡的 'wind_speed' 已經是蒲福風級
    comfort_max_desc = processed_data_for_outfit_logic.get('comfort_max_desc', '')
    comfort_min_desc = processed_data_for_outfit_logic.get('comfort_min_desc', '')
    uvi = processed_data_for_outfit_logic.get('uvi')

    # --- 檢查核心數據是否存在，如果沒有則返回預設值 ---
    # 這是一個防禦性編程，確保函式在接收到不完整的數據時，不會崩潰，而是回傳一個友善的錯誤訊息，提高了程式的健壯性
    if any(val is None for val in [max_feels_like_temp, min_feels_like_temp, temp_range_diff, avg_humidity, pop, wind_speed, uvi]):
        logger.warning("未來預報穿搭建議所需的核心數據不完整。")
        return {"suggestion_text": ["未來天氣預報資料不足，無法提供詳細穿搭建議。"], "suggestion_image_url": IMAGE_URLS["NO_DATA"]}

    # --- 生成穿搭建議文本 ---
    final_suggestions = [] # 使用列表儲存建議的各部分，方便後面組裝
    image_url = IMAGE_URLS["DEFAULT"] # 預設圖

    # --- 根據體感溫度給出穿搭建議 ---
    """
    體感溫度是判斷穿著最直接的依據。
    這裡優先處理極端天氣（極熱和極冷），因為這些情況下的穿搭建議最為關鍵，接著再處理溫和的天氣，確保建議的準確性和優先順序。
    這個區塊也會設定一個初步的圖片 URL。
    """
    # 極端高溫
    if max_feels_like_temp >= 32:
        final_suggestions.append("• 預期天氣極度炎熱，體感悶熱，務必穿著最輕薄、透氣且吸濕排汗的衣物，如棉麻或機能性短袖、短褲或裙子。")
        image_url = IMAGE_URLS["HOT"]
    # 極端低溫
    elif min_feels_like_temp <= 12:
        final_suggestions.append("• 天氣偏冷，體感寒涼，外出請務必準備厚外套、毛衣或羽絨服，並注意頸部和四肢保暖。")
        image_url = IMAGE_URLS["COLD"]
    # 溫暖舒適區 (在極端溫度之後判斷，如果沒有極端溫度，則給出一般建議)
    elif 28 <= max_feels_like_temp < 32 and min_feels_like_temp >= 24:
        final_suggestions.append("• 白天炎熱，但整體體感舒適，建議穿著涼爽短袖，若進出冷氣房可備薄開衫。")
        image_url = IMAGE_URLS["WARM"]
    # 涼爽舒適區
    elif 20 <= max_feels_like_temp < 28 and min_feels_like_temp >= 16:
        final_suggestions.append("• 天氣涼爽宜人，建議穿著薄長袖或搭配薄外套，早晚可能微涼。")
        image_url = IMAGE_URLS["COOL"] # 涼爽圖
    else: # 涵蓋其他溫和情況和較大溫差，給出一般舒適建議
        final_suggestions.append("• 氣溫適中，穿著舒適即可，建議採用洋蔥式穿搭以應對可能的氣溫變化。")
        image_url = IMAGE_URLS["COMFORTABLE"]

    # --- 針對降雨情況進行補充 ---
    """
    根據降雨機率 (pop) 和天氣現象 (weather_phenomena) 來追加建議。
    包含一個圖片覆蓋的邏輯：如果降雨是當天最主要的氣象特徵，則會用降雨圖片覆蓋之前的溫度圖片，以突出最關鍵的建議。
    """
    if pop is not None:
        if pop >= 70:
            final_suggestions.append("• 降雨機率極高，有大雨可能，外出務必攜帶堅固雨具，建議穿著防水外套和鞋子。")
            # 如果主要溫度建議沒有賦予更優先的圖片 (如極熱/極冷)，則覆蓋為大雨圖
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

    # --- 溫差建議（補充）---
    # 在溫度建議的基礎上，額外補充溫差較大的提醒
    if temp_range_diff >= 8: # 如果溫差大於等於 8 度，且已經有基礎建議
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，早晚注意保暖，建議攜帶外套。")
    elif temp_range_diff >= 5:
        final_suggestions.append(f"• 日夜溫差約 {temp_range_diff}°C，建議備薄外套。")

    # --- 補充濕度建議 ---
    # 包含圖片覆蓋邏輯，確保在特定情況下，顯示最相關的圖片
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

    # --- 補充風速/風寒建議 (使用蒲福風級數字判斷和描述) ---
    if wind_speed is not None:
        if wind_speed >= 7 and (min_feels_like_temp is None or min_feels_like_temp < 20): # 疾風或更高，且氣溫偏涼
            final_suggestions.append(f"• 風力屬於 {wind_speed}，注意風寒效應，建議穿著防風外套，並固定帽子或髮型。")
            if min_feels_like_temp is not None and min_feels_like_temp < 15:
                final_suggestions.append("• 尤其注意頭部、頸部保暖。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["WINDY"]
        elif wind_speed >= 5 and (min_feels_like_temp is None or min_feels_like_temp < 25): # 清風或更高，且氣溫偏涼
            final_suggestions.append(f"• 風力屬於 {wind_speed}，體感溫度可能略低，可備一件薄防風外套。")
            if image_url not in [IMAGE_URLS["HOT"], IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["WINDY"]
        elif wind_speed >= 3 and (min_feels_like_temp is not None and min_feels_like_temp < 15): # 微風或更高，但氣溫較低
            final_suggestions.append(f"• 風力屬於 {wind_speed}，雖然風不大但天氣微涼，請注意保暖。")

    # --- 補充紫外線指數建議 ---
    if uvi is not None:
        if uvi >= 11: # 危險級
            final_suggestions.append(f"• 紫外線指數高達 {uvi}！戶外活動務必全程做好防曬，包括防曬乳、帽子、太陽眼鏡、遮陽傘，建議穿著長袖、輕薄透氣的衣物。")
            # 優先使用最高等級的 UVI 圖，但如果已經是極端天氣（冷、大雨），不覆蓋
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                 image_url = IMAGE_URLS["HIGH_UVI"]
        if uvi >= 8: # 極量或過量
            final_suggestions.append(f"• 紫外線指數高達 {uvi}！長時間戶外活動請加強防曬，建議戴太陽眼鏡、遮陽帽，塗抹防曬乳。")
            if max_feels_like_temp is not None and max_feels_like_temp >= 25: # 在炎熱天氣下，紫外線更需要強調防曬衣物
                final_suggestions.append("• 可考慮穿著防曬衣物。")
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"]]:
                image_url = IMAGE_URLS["HIGH_UVI"]
        elif uvi >= 6: # 中量或高量
            final_suggestions.append(f"• 紫外線指數為 {uvi}，外出建議戴太陽眼鏡、遮陽帽，並塗抹防曬乳。")
            if image_url not in [IMAGE_URLS["COLD"], IMAGE_URLS["HEAVY_RAIN"], IMAGE_URLS["RAINY_FORECAST"], IMAGE_URLS["HIGH_UVI"]]:
                image_url = IMAGE_URLS["HIGH_UVI"]
        elif uvi >= 3: # 中等
            final_suggestions.append(f"• 紫外線指數為 {uvi}，外出可戴太陽眼鏡。")
    else:
        final_suggestions.append("• 紫外線指數資訊不完整。")

    # --- 舒適度文字描述補充 ---
    if comfort_max_desc is not None and comfort_min_desc is not None:
        if any(word in comfort_max_desc for word in ["悶熱", "不舒適", "炎熱"]) and not any("悶熱" in s or "炎熱" in s for s in final_suggestions):
            final_suggestions.append("• 體感偏向悶熱，請盡量減少衣物層次。")
        if any(word in comfort_min_desc for word in ["涼", "冷", "寒冷"]) and not any("寒涼" in s or "冷" in s for s in final_suggestions):
            final_suggestions.append("• 夜間或清晨可能感覺涼冷，注意身體末梢保暖。")

    # --- 確保至少有一條建議 ---
    # 這是一個最終的保護機制
    # 即使所有條件判斷都沒有被觸發，函式仍會確保回傳一個預設的建議，避免回傳空值，讓程式能夠穩定運行，並提供有用的資訊
    if not final_suggestions:
        final_suggestions.append("• 今日天氣狀況大致良好，穿著舒適即可。")
        if image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # --- 去重並合併建議 ---
    """
    在多個條件判斷中，可能會產生重複或相似的建議。
    這裡使用 `dict.fromkeys` 的技巧可以高效的去除重複項目，同時保持建議的原始順序。
    確保最終呈現給用戶的建議列表是乾淨、精簡且邏輯連貫的。
    """
    final_suggestions = list(dict.fromkeys(final_suggestions)) # 利用字典的特性去重並保持順序

    # --- 回傳最終的穿搭建議 ---
    """
    這裡將處理好的文字建議列表和最終選定的圖片 URL 封裝在一個字典中回傳。
    這將「資料處理」與「資料呈現」分離。
    這個函式只負責產生建議，不負責建立 Flex Message。
    回傳的字典將作為下一個步驟（即 Flex Message 產生器）的輸入，這種清晰的職責劃分使得整個系統的設計更為模組化。
    """
    logger.debug(f"未來預報穿搭建議生成: {final_suggestions}, 圖: {image_url}")
    return {
        "suggestion_text": final_suggestions,
        "suggestion_image_url": image_url
    }