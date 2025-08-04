# weekend_weather/weekend_handler.py
import json
import logging
from typing import Dict, List, Optional
from linebot.v3.messaging.models import Message, TextMessage, FlexMessage, FlexBubble, FlexCarousel
from linebot.v3.webhooks.models import PostbackEvent

from config import CWA_API_KEY

# 引入必要的工具函數和轉換器
from utils.api_helper import get_messaging_api
from utils.text_processing import normalize_city_name
from utils.user_data_manager import get_user_state, get_default_city
from utils.line_common_messaging import send_line_reply_message, send_api_error_message

from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather
# from life_reminders.weekend_weather_flex import build_weekend_weather_flex
from weekend_weather.weekend_forecast_converter import get_weekend_forecast_flex_messages 

logger = logging.getLogger(__name__)

# 將核心邏輯封裝成一個獨立的函式，以便其他模組可以重複使用
def create_weekend_weather_message(county_name: str) -> Optional[List[Message]]:
    """
    此函式從 API 取得並處理天氣數據，最終生成 Flex Message 或 TextMessage。
    """
    try:
        normalized_location_name = normalize_city_name(county_name)

        # 1. 從中央氣象局 API 獲取天氣預報數據
        cwa_data = get_cwa_forecast_data(CWA_API_KEY, normalized_location_name)
        if not cwa_data or not cwa_data.get("records"): # 檢查 cwa_data 是否為空或沒有 'records' 鍵
            logger.warning(f"無法取得 {county_name} 的天氣預報資訊。API 返回空數據或無效格式。")
            return [TextMessage(text=f"抱歉，無法取得 {county_name} 的天氣預報資訊。")]
        
        # 2. 解析並格式化天氣數據
        parsed_forecast_weather = parse_forecast_weather(cwa_data, normalized_location_name)
        if not parsed_forecast_weather or not parsed_forecast_weather.get("forecast_periods"):
            logger.error(f"無法從取得的週末天氣資料中解析或格式化出 {normalized_location_name} 的天氣資訊。")
            return [TextMessage(text=f"抱歉，無法顯示 {normalized_location_name} 的天氣資訊卡片。請稍候再試。")]
        
        # 3. 調用 weekend_forecast_converter 來篩選週末數據並生成 Flex Message
        weekend_weather_bubbles = get_weekend_forecast_flex_messages(parsed_forecast_weather)

        messages_to_send: List[Message] = []
        if weekend_weather_bubbles:
            # 將多個 Flex Bubble 包裝在 FlexCarousel 中
            messages_to_send.append(FlexMessage(
                alt_text=f"{normalized_location_name} 週末天氣預報",
                contents=FlexCarousel(contents=weekend_weather_bubbles)
            ))
        else:
            logger.warning(f"沒有為 {normalized_location_name} 生成週末天氣預報 Flex Bubbles。")
            messages_to_send.append(TextMessage(text=f"目前沒有 {normalized_location_name} 的週末天氣預報資訊。"))

        return messages_to_send
    
    except Exception as e:
        logger.exception(f"生成週末天氣 Flex Message 時發生錯誤: {e}")
        return [TextMessage(text="抱歉，查詢週末天氣時發生內部錯誤。")]

def handle_weekend_weather_postback(api, event) -> bool:
    """
    處理週末天氣預報的 Postback 事件。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    logger.info(f"處理週末天氣 postback，用戶: {user_id}")

    # 1. 獲取用戶設定的城市
    county_name = get_default_city(user_id)
    if not county_name:
        county_name = "臺中市" # 這裡可以設定一個最常用的預設城市
        logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{county_name}")

    # 這裡直接呼叫我們新封裝的函式
    messages_to_send = create_weekend_weather_message(county_name)
        
    # 然後回覆訊息
    if messages_to_send:
        send_line_reply_message(api, reply_token, messages_to_send)
        logger.info(f"✅ 成功發送 {county_name} 週末天氣預報和穿搭建議。")
    return True

    """
    # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
    # 使用 line_common_messaging 中的 format_flex_message 函數
    flex_msg_to_send = FlexMessage(
        alt_text=f"{normalized_location_name} 即時天氣",
        contents=weather_flex_bubble # 直接傳入 FlexBubble 物件
    )

    # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件列表)
    # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
    send_line_reply_message(api, reply_token, [flex_msg_to_send])
    return True # 訊息已處理
    """