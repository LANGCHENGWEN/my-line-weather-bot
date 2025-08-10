# weather_today/today_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging
from typing import Dict, Optional
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import MessageEvent

# 從您的設定檔中導入 API 金鑰
from config import CWA_API_KEY

from utils.text_processing import normalize_city_name

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import (
    send_line_reply_message, send_api_error_message
)

# 導入用戶數據管理器 (用於獲取用戶預設城市)
from utils.firestore_manager import set_user_state, get_default_city

# 導入我們新的數據聚合器
from .today_weather_aggregator import get_today_all_weather_data

from .today_weather_flex_messages import build_daily_weather_flex_message

logger = logging.getLogger(__name__)
    
def build_and_send_today_weather_message(api, reply_token: str, all_weather_data: Optional[Dict], city_name: str) -> None:
    """
    私有輔助函式：根據聚合後的完整數據建構 Flex Message 並回覆。
    如果數據為 None 或建構失敗，會發送文字訊息作為備援。
    """
    if not all_weather_data:
        # 如果沒有聚合好的數據，直接發送錯誤文字訊息
        message_text = f"抱歉，無法取得 {city_name} 的今日天氣資訊，請稍候再試。"
        send_line_reply_message(api, reply_token, [TextMessage(text=message_text)])
        logger.warning(f"未能為 {city_name} 建立今日天氣訊息，已發送文字備援。")
        return
        
    try:
        # 1. 直接建立 Line Bot SDK 的 FlexMessage 物件
        flex_message_to_send = build_daily_weather_flex_message(
            location=all_weather_data.get("locationName", city_name),
            parsed_weather=all_weather_data.get("general_forecast", {}),
            parsed_data=all_weather_data.get("hourly_forecast", []),
            parsed_uv_data=all_weather_data.get("uv_data", {})
        )

        if not isinstance(flex_message_to_send, FlexMessage):
            raise ValueError("build_daily_weather_flex_message 未返回 FlexMessage 物件。")
        
        # 2. 發送回覆訊息
        send_line_reply_message(api, reply_token, [flex_message_to_send])
        logger.info(f"已向用戶發送 {city_name} 今日天氣 Flex Message。")

    except Exception as e:
        logger.exception(f"建構或發送 {city_name} Flex Message 時發生錯誤: {e}")
        # 發生錯誤時發送文字訊息作為備援
        message_text = f"抱歉，處理 {city_name} 的今日天氣卡片時發生內部錯誤，請稍候再試。"
        send_line_reply_message(api, reply_token, [TextMessage(text=message_text)])

def handle_today_message(api, event: MessageEvent) -> bool:
    """
    處理「今日天氣」或城市名稱的訊息輸入。
    - 若訊息包含「今日天氣」 ➜ 顯示預設城市天氣
    - 若訊息為有效的城市名稱 ➜ 顯示該城市的天氣
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 情境一：輸入「今日天氣」關鍵字
    if "今日天氣" in message_text:
        logger.info(f"用戶 {user_id} 查詢今日天氣。")

        # 獲取用戶的預設城市 (假設已經設定好，如果沒有則使用預設值)
        # 您需要確保 get_default_city 函數能正確返回城市名稱
        user_city = get_default_city(user_id)
        if not user_city:
            user_city = "臺中市" # 這裡可以設定一個最常用的預設城市
            logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{user_city}")

        # 1. 呼叫數據聚合器，一口氣取得所有資料
        all_weather_data = get_today_all_weather_data(user_city)

        # 2. 建構並發送訊息
        build_and_send_today_weather_message(api, reply_token, all_weather_data, user_city)

        set_user_state(user_id, 'awaiting_today_city_input', data={'city': user_city})
        logger.info(f"已為用戶 {user_id} 設定狀態為 'awaiting_today_city_input'。")
    
    return True
    
# --- 通用回覆函式：今日天氣預報 (F-C0032-001 - 今明36小時) ---
def reply_today_weather_of_city(api, reply_token: str, user_id: str, city_name: str) -> None:
    """
    直接根據 city_name 抓今日 (36小時) 天氣預報資料、組 Flex、回覆。
    """
    normalized_city_name = normalize_city_name(city_name)
    logger.info(f"正在為用戶 {user_id} 查詢 {normalized_city_name} 的今日天氣預報。")

    # 1. 呼叫數據聚合器，一口氣取得所有資料
    all_weather_data = get_today_all_weather_data(normalized_city_name)

    # 2. 建構並發送訊息
    build_and_send_today_weather_message(api, reply_token, all_weather_data, normalized_city_name)
    
    return False # 這個 handler 沒有處理這個訊息