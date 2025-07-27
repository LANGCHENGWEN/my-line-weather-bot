# utils/today_outfit_logic.py
import pytz
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta

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
    "WINDY": "https://i.imgur.com/windy_outfit.png",

    "HIGH_HUMIDITY": "https://i.imgur.com/high_humidity.png",
    "DRY_WEATHER": "https://i.imgur.com/dry_weather.png",
    "HIGH_UVI": "https://i.imgur.com/high_uvi.png"
}

# --- 新增的今日穿搭建議函式 ---
def get_outfit_suggestion_for_today_weather(
    location: str,
    hourly_forecast: List[Dict[str, Any]],
    general_forecast: Dict[str, Any],
    uv_data: Dict[str, Any] | None
) -> Dict[str, Any]:
    """
    根據綜合天氣數據生成每日穿搭建議。
    Args:
        location (str): 查詢天氣的地點。
        hourly_forecast (List[Dict[str, Any]]): 從 F-D0047-089 解析後的逐小時天氣數據列表。
                                                 包含體感溫度、相對濕度、風向、風速（已帶單位及原始數值，風級）。
        general_forecast (Dict[str, Any]): 從 F-C0032-001 解析後的整體天氣狀況數據字典。
                                             包含天氣現象、降雨機率、最低溫度、最高溫度、舒適度指數、
                                             格式化溫度範圍、紫外線指數（降雨機率及溫度範圍已帶單位）。
        uv_data (Dict[str, Any] | None): 已經解析好的紫外線指數數據字典 (來自 O-A0005-001)。
                                         現在包含 'UVIndexRaw' 和 'UVIndexFormatted'。
    Returns:
        Dict[str, Any]: 包含穿搭建議文本及天氣數據的字典。
    """
    logger.debug(f"[OutfitLogic] Generating outfit suggestion for {location}.")

    # --- 初始化逐時數據相關變數為 N/A 或 None ---
    # 格式化字符串，用於顯示
    formatted_feels_like = "N/A"
    formatted_humidity = "N/A"
    formatted_wind_speed = "N/A" # 這裡會是 m/s 單位
    formatted_wind_scale = "N/A" # 這是 "X級 (描述)" 的字串

    # 原始數值，用於邏輯判斷
    apparent_temp_raw = None
    humidity_raw = None
    wind_speed_raw = None # 原始 m/s 數值
    wind_scale_raw = None # **現在這裡將接收純數字的風級**

    if not hourly_forecast:
        logger.warning(f"未能找到 {location} 可用的逐時天氣預報數據，無法提供詳細穿搭建議。")
    else:
        # --- 從 F-D0047-089 獲取當前或最近的逐時預報數據 ---
        # 設定為台北時區 (UTC+8)
        taipei_tz = pytz.timezone('Asia/Taipei')
        # 獲取當前時間並將其設定為台北時區
        now = datetime.now(taipei_tz)
        logger.debug(f"當前時區感知時間 (now): {now}")

        # 尋找最接近當前時間或之後的第一個預報數據點
        current_hour_data = None
    
        # 尋找最接近當前時間或之後的第一個預報數據點
        for data_point in hourly_forecast:
            try:
                # 解析 DataTime，如果它是時區樸素的，則本地化它
                forecast_time_str = data_point["DataTime"]
                forecast_time = datetime.fromisoformat(forecast_time_str)

                if forecast_time.tzinfo is None:
                    # 如果是時區樸素的，則本地化為台北時區
                    logger.warning(f"預報時間 '{forecast_time_str}' 為時區樸素，嘗試本地化為台北時區。")
                    forecast_dt = taipei_tz.localize(forecast_time)
                else:
                    # 如果已經是時區感知的，則轉換為台北時區 (如果不是)
                    forecast_dt = forecast_dt.astimezone(taipei_tz)

                logger.debug(f"處理預報時間: {forecast_time_str} -> 時區感知時間: {forecast_dt}")

                # 比較時區感知的日期時間
                if forecast_dt >= now:
                    current_hour_data = data_point
                    break
            except ValueError as e:
                logger.error(f"解析逐時預報時間 '{data_point.get('DataTime')}' 失敗: {e}", exc_info=True)
                continue # 跳過無法解析的時間
            except Exception as e:
                logger.error(f"處理逐時預報時間 '{data_point.get('DataTime')}' 時發生未知錯誤: {e}", exc_info=True)
                continue
    
        # 如果沒有未來預報（例如已經過了預報的所有時間），則取最後一個預報點
        if not current_hour_data and hourly_forecast:
            current_hour_data = hourly_forecast[-1]
            logger.warning(f"未找到未來預報，使用最後一個可用的預報數據點: {current_hour_data.get('DataTime')}")
        
        if current_hour_data:
            # 直接提取已格式化的字串 (用於顯示)
            # 提取 F-D0047-089 數據
            formatted_feels_like = current_hour_data.get("apparent_temp", "N/A") # 這裡使用 parse_3days_weather 調整後的鍵名
            formatted_humidity = current_hour_data.get("humidity", "N/A") # 使用調整後的鍵名
            formatted_wind_speed = current_hour_data.get("wind_speed", "N/A") # 使用調整後的鍵名
            # formatted_wind_scale = current_hour_data.get("wind_scale", "N/A") # 直接從 parser 獲取格式化後的風級
            # wind_direction = current_hour_data.get("wind_direction", "N/A") # 如果需要，這裡也可以提取
            
            # --- 這裡獲取格式化後的字串和原始數字風級 ---
            formatted_wind_scale = current_hour_data.get("wind_scale_formatted", "N/A")
            wind_scale_raw = current_hour_data.get("wind_scale_raw") # **用於判斷**

            # 提取原始數值 (用於邏輯判斷)
            apparent_temp_raw = current_hour_data.get("apparent_temp_raw")
            humidity_raw = current_hour_data.get("humidity_raw")
            wind_speed_raw = current_hour_data.get("wind_speed_raw") # 這是 m/s 原始數值

            logger.debug(f"成功提取逐時數據: 體感: {formatted_feels_like} ({apparent_temp_raw}), 濕度: {formatted_humidity} ({humidity_raw}), 風速: {formatted_wind_speed} ({wind_speed_raw})")
        else:
            logger.warning(f"未能找到 {location} 可用的逐時天氣預報數據，體感溫度、濕度、風速將為 N/A。")

    # --- 從 general_forecast (F-C0032-001) 提取數據 ---
    # 確保這裡使用的鍵名與 weather_today_parser.py 的輸出一致
    date_full_formatted = general_forecast.get("date_full_formatted", "N/A")
    weather_phenomenon = general_forecast.get("weather_phenomenon", "無資訊")    
    max_temp_raw = general_forecast.get("max_temp", "N/A") # 獲取原始數值用於判斷
    min_temp_raw = general_forecast.get("min_temp", "N/A") # 獲取原始數值用於判斷
    formatted_temp_range = general_forecast.get("formatted_temp_range", "N/A") # 從解析器直接獲取帶 °C 的字串
    formatted_pop = general_forecast.get("pop", "N/A") # 從解析器直接獲取帶 % 的字串
    # comfort_index = general_forecast.get("comfort_index", "N/A") # 應該是 'comfort_index'
    # uv_index = "N/A" # F-C0032-001 不包含紫外線指數，需要其他數據源

    # 將降雨機率轉換為數值，用於邏輯判斷
    precipitation_prob_int = 0
    if isinstance(formatted_pop, str) and formatted_pop.endswith('%'):
        try:
            precipitation_prob_int = int(formatted_pop[:-1])
        except ValueError:
            pass # 保持為 0 或預設值

    # 將溫度範圍的原始數值轉換為 int，用於備用邏輯判斷
    min_temp_int = int(min_temp_raw) if isinstance(min_temp_raw, str) and min_temp_raw.isdigit() else None
    max_temp_int = int(max_temp_raw) if isinstance(max_temp_raw, str) and max_temp_raw.isdigit() else None

    # --- 獲取紫外線指數值 (現在直接獲取格式化字串和原始數值) ---
    uv_index_formatted_str = "N/A" # 預設顯示值
    uv_index_raw_val = None # 預設原始數值

    if uv_data and "UVIndexFormatted" in uv_data:
        uv_index_formatted_str = uv_data["UVIndexFormatted"]
        uv_index_raw_val = uv_data.get("UVIndexRaw") # 獲取原始數值，用於判斷 (如果需要)
        logger.info(f"成功接收格式化紫外線指數: {uv_index_formatted_str}")
    else:
        logger.warning("未接收到有效的紫外線指數資訊。")

    # --- 生成穿搭建議文本 ---
    suggestion_text = [] # 使用列表儲存建議的各部分，方便後面組裝
    suggestion_image_url = IMAGE_URLS["DEFAULT"] # 預設圖
    
    # 根據體感溫度給出基礎建議
    if apparent_temp_raw is not None:
        # 添加濕度判斷的輔助變數或直接判斷
        is_high_humidity = humidity_raw is not None and humidity_raw >= 75 # 範例：高濕度定義為75%以上
        is_low_humidity = humidity_raw is not None and humidity_raw <= 40 # 範例：低濕度定義為40%以下

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
        else: # apparent_temp_int < 15
            base_suggestion = "• 天氣非常寒冷，務必做好保暖！建議穿著厚毛衣、羽絨服或保暖大衣，並搭配圍巾、手套等配件。"
            if is_high_humidity:
                base_suggestion = "• 天氣非常寒冷且濕度極高，體感非常濕冷，務必做好保暖！建議穿著厚毛衣、具備防水防風功能的羽絨服或保暖大衣，並搭配圍巾、手套等配件，避免寒氣入侵。"
            elif is_low_humidity:
                base_suggestion = "• 天氣非常寒冷且乾燥，務必做好保暖！建議穿著厚毛衣、羽絨服或保暖大衣，並搭配圍巾、手套等配件，同時注意全身的保濕。"
            suggestion_text.append(base_suggestion)
            suggestion_image_url = IMAGE_URLS["FREEZING"]
    else:
        # 如果體感溫度 N/A，則嘗試根據最高/最低氣溫來給建議 (作為備用)
        if min_temp_int is not None and max_temp_int is not None:
            avg_temp = (min_temp_int + max_temp_int) / 2
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

    # --- 針對降雨情況進行補充 (更詳細) ---
    if "豪雨" in weather_phenomenon or "大雨" in weather_phenomenon or precipitation_prob_int > 50: # 假定50%以上為大雨
        suggestion_text.append("• 降雨機率極高，外出務必攜帶雨具，建議穿著防水性佳的衣物及鞋子。")
        suggestion_image_url = IMAGE_URLS["HEAVY_RAIN"]
    elif "午後雷陣雨" in weather_phenomenon:
        suggestion_text.append("• 午後有雷陣雨，外出請攜帶雨具。")
        suggestion_image_url = IMAGE_URLS["LIGHT_RAIN"] # 或者更適合的雷陣雨圖
    elif "陣雨" in weather_phenomenon or "雷雨" in weather_phenomenon or "雨" in weather_phenomenon:
        # 這裡可以根據 precipitation_value 再次細分小雨、中雨
        if 0 < precipitation_prob_int <= 50: # 假設 0-50% 為一般陣雨或小雨
            suggestion_text.append("• 降雨機率較高，建議攜帶雨具，穿著防潑水衣物或備薄外套。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]
        elif precipitation_prob_int == 0 and ("陣雨" in weather_phenomenon or "雨" in weather_phenomenon):
            # 描述有雨但降水量為0，可能是短暫或預期有雨但尚未發生
            suggestion_text.append("• 可能有短暫降雨，建議攜帶雨具。")
            suggestion_image_url = IMAGE_URLS["RAINY_CURRENT"]

    """
    # 考慮濕度影響
    relative_humidity_int = int(relative_humidity) if isinstance(relative_humidity, str) and relative_humidity.isdigit() else None
    if relative_humidity_int is not None:
        if apparent_temp_int is not None:
            if relative_humidity_int >= 80 and apparent_temp_int >= 28:
                suggestion_parts.append("濕度較高，體感會更悶熱不適，請選擇排汗、吸濕快乾的材質。")
            elif relative_humidity_int >= 85 and apparent_temp_int < 20:
                suggestion_parts.append("濕度高可能感覺濕冷，請務必加強防潮與保暖。")
    """

    # 考慮風速影響 (使用來自 parser 的 wind_scale_raw 進行判斷)
    if wind_scale_raw is not None and wind_scale_raw != "N/A" and apparent_temp_raw is not None:
        if wind_scale_raw >= 7: # 強風以上 (7級或更高)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，風寒效應顯著，請特別注意防風保暖，務必穿著防風外套，並加強頭頸部保暖。")
            if suggestion_image_url == IMAGE_URLS["DEFAULT"]:
                suggestion_image_url = IMAGE_URLS["WINDY"]
        elif wind_scale_raw >= 4: # 和風到勁風 (4-6級)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，體感溫度可能略低，建議可備一件薄防風外套。")
            if suggestion_image_url == IMAGE_URLS["DEFAULT"]:
                suggestion_image_url = IMAGE_URLS["WINDY"]
        elif wind_scale_raw >= 3: # 微風 (3級)
            suggestion_text.append(f"• 風力屬於 {formatted_wind_scale}，體感略受影響，一般輕薄外套足以應對。")
        else: # 0-2級，微風以下
            suggestion_text.append("• 今日風力較弱，穿搭上無需特別考慮風速影響。")
    else:
        suggestion_text.append("• 風速資訊不完整，請留意實際風力狀況。")

    # --- 根據紫外線指數添加建議 ---
    if uv_index_raw_val is not None: # 使用原始數值進行判斷
        if uv_index_raw_val >= 11: # 危險
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_formatted_str}！戶外活動務必全程做好防曬，包括防曬乳、帽子、太陽眼鏡、遮陽傘。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["HOT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"] # 繼續使用高紫外線圖片
        elif uv_index_raw_val >= 8: # 過量
            suggestion_text.append(f"• 紫外線指數高達 {uv_index_formatted_str}！長時間戶外活動請加強防曬，建議戴太陽眼鏡、遮陽帽，塗抹防曬乳。")
            # 如果當前圖片還是預設，或者適合替換，則替換為高紫外線圖片
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["HOT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"]
        elif uv_index_raw_val >= 6: # 高
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}，外出建議戴太陽眼鏡、遮陽帽，並塗抹防曬乳。")
            if suggestion_image_url in [IMAGE_URLS["DEFAULT"], IMAGE_URLS["WARM"], IMAGE_URLS["COMFORTABLE"]]:
                suggestion_image_url = IMAGE_URLS["HIGH_UVI"] # 也可以考慮用這個圖
        elif uv_index_raw_val >= 3: # 中
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}，外出可戴太陽眼鏡。")
        else: # 低
            suggestion_text.append(f"• 紫外線指數為 {uv_index_formatted_str}。")
    else:
        suggestion_text.append("• 紫外線指數資訊不完整。")

    # 如果沒有特定建議，給出預設文字
    if not suggestion_text:
        suggestion_text.append("• 今天天氣狀況良好，穿著舒適即可。")
        if suggestion_image_url == IMAGE_URLS["DEFAULT"]: # 如果前面沒有圖，給個預設
            suggestion_image_url = IMAGE_URLS["COMFORTABLE"] # 預設溫和天氣圖

    # 最後組裝建議文本
    # final_suggestion_text = "\n".join(suggestion_text)

    # 構造最終返回給 Flex Message 的數據字典
    outfit_info_to_return = {
        "outfit_suggestion_text": suggestion_text,
        "suggestion_image_url": suggestion_image_url, # 這裡可以根據天氣調整圖片
        "date_full_formatted": date_full_formatted,
        "weather_phenomenon": weather_phenomenon,
        "feels_like": formatted_feels_like,
        "formatted_temp_range": formatted_temp_range,
        "humidity": formatted_humidity,
        "pop": formatted_pop, # 這裡傳原始數字，由 Flex Message 加上 %
        "wind_speed": formatted_wind_speed, # 這裡仍然保持 m/s 的原始格式，因為它是從解析器直接拿的
        "wind_scale": formatted_wind_scale, # 現在是 "X級 (描述)" 的字串
        "uv_index": uv_index_formatted_str
    }

    logger.debug(f"今日穿搭建議生成及數據回傳: {outfit_info_to_return}")
    return outfit_info_to_return

    """
    logger.debug("[OutfitLogic] 處理今日穿搭建議，呼叫 get_outfit_suggestion_for_current_weather。")
    return get_outfit_suggestion_for_today_weather(today_weather_data)
    """