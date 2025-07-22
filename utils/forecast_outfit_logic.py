# utils/forecast_outfit_logic.py
import logging

logger = logging.getLogger(__name__)

def get_outfit_suggestion_for_forecast_weather(forecast_data: list) -> dict:
    """
    根據未來預報數據提供綜合穿搭建議。
    Args:
        forecast_data (list): 未來幾天的預報數據列表，每個元素是 dict 包含 'date', 'min_temp', 'max_temp', 'pop' (降水機率) 等。
                              此格式應與 weather/weather_api.py 的 get_cwa_forecast_data 輸出相符。
    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """
    if not forecast_data:
        return {"suggestion_text": "未來天氣預報資料不足。", "suggestion_image_url": "https://i.imgur.com/no_data.png"}

    # 簡單的邏輯：判斷未來幾天是否有明顯的冷暖變化或持續降雨
    # 對於只有一天的預報，min_temp 和 max_temp 將是同一天的範圍
    if len(forecast_data) == 1:
        avg_min_temp = forecast_data[0].get('min_temp', 0)
        avg_max_temp = forecast_data[0].get('max_temp', 0)
        # 對於單日，用當日的 PoP (降水機率)
        avg_pop = forecast_data[0].get('pop', 0) 
        # 單日天氣現象
        forecast_weather_phenomenon = forecast_data[0].get('weather_phenomenon', '')
    else:
        avg_min_temp = sum([d.get('min_temp', 0) for d in forecast_data]) / len(forecast_data)
        avg_max_temp = sum([d.get('max_temp', 0) for d in forecast_data]) / len(forecast_data)
        avg_pop = sum([d.get('pop', 0) for d in forecast_data]) / len(forecast_data)
        
        # 對於多天預報，將所有天氣現象合併並去重
        all_weather_phenomena = []
        for d in forecast_data:
            phen = d.get('weather_phenomenon', '')
            if phen:
                # 假設以逗號分隔，並且要處理如 "多雲, 陰" 這種情況
                all_weather_phenomena.extend([p.strip() for p in phen.split(',') if p.strip()]) 
        forecast_weather_phenomenon = ", ".join(list(set(all_weather_phenomena)))

    suggestion_text = "未來幾天天氣變化不大。"
    suggestion_image_url = "https://i.imgur.com/forecast_default.png"

    # 判斷氣溫趨勢
    if avg_min_temp < 15:
        suggestion_text = "未來幾天氣溫偏低，建議準備保暖衣物。"
        suggestion_image_url = "https://i.imgur.com/cold_forecast.png"
    elif avg_max_temp >= 30:
        suggestion_text = "未來幾天氣溫較高，請準備輕便衣物，並注意防曬。"
        suggestion_image_url = "https://i.imgur.com/hot_forecast.png"
    elif 25 <= avg_max_temp < 30 and avg_min_temp >= 20:
        suggestion_text = "未來幾天氣溫舒適，穿著薄長袖或短袖皆可。"
        suggestion_image_url = "https://i.imgur.com/warm_weather_outfit.png"

    # 判斷降雨情況
    if avg_pop > 50 or "雨" in forecast_weather_phenomenon or "陣雨" in forecast_weather_phenomenon or "雷雨" in forecast_weather_phenomenon: 
        suggestion_text += " 多數時間有降雨，外出請務必攜帶雨具。"
        # 如果未來幾天主要都是雨，則替換圖片
        suggestion_image_url = "https://i.imgur.com/rainy_forecast.png"

    logger.debug(f"預報穿搭建議生成: {suggestion_text}, 圖: {suggestion_image_url}")
    return {"suggestion_text": suggestion_text, "suggestion_image_url": suggestion_image_url}