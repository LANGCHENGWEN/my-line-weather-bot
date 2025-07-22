# utils/today_outfit_logic.py
import logging

logger = logging.getLogger(__name__)

# --- 新增的今日穿搭建議函式 ---
def get_outfit_suggestion_for_today_weathe(today_weather_data: dict) -> dict:
    """
    根據今日天氣數據提供穿搭建議。
    此函數直接呼叫 get_outfit_suggestion_for_current_weather，因為邏輯相同。
    Args:
        today_weather_data (dict): 包含今日天氣資訊的字典，格式與 current_weather_data 相同。
                                   來自 weather_current_parser.py 輸出後的格式。
    Returns:
        dict: 包含 'suggestion_text' 和 'suggestion_image_url' 的字典。
    """
    logger.debug("[OutfitLogic] 處理今日穿搭建議，呼叫 get_outfit_suggestion_for_current_weather。")
    return get_outfit_suggestion_for_current_weather(today_weather_data)