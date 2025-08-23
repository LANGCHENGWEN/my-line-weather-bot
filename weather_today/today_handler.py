# weather_today/today_handler.py
"""
處理「今日天氣」相關訊息的核心邏輯。
主要職責：
1. 處理用戶輸入：根據用戶傳入的文字訊息（例如「今日天氣」或特定的城市名稱），判斷要執行的操作。
2. 協調數據獲取：呼叫 `today_weather_aggregator` 獲取不同來源的今日天氣數據，例如 36 小時預報、未來 3 天天氣預報和紫外線指數。
3. 格式化訊息：將所有聚合好的數據傳遞給 `today_weather_flex_messages`，生成視覺化的 Flex Message。
4. 回覆用戶：將生成的 Flex Message 發送給 LINE 用戶；如果過程中發生任何錯誤，會發送一個友善的文字訊息作為備援。
"""
import logging
from typing import Dict, Optional
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import MessageEvent

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import set_user_state, get_default_city # 導入用戶數據管理器

from .today_weather_aggregator import get_today_all_weather_data # 導入數據聚合器
from .today_weather_flex_messages import build_daily_weather_flex_message

logger = logging.getLogger(__name__)
    
# --- 輔助函式：根據聚合後的完整數據建構 Flex Message 並回覆 ---
def build_and_send_today_weather_message(api, reply_token: str, all_weather_data: Optional[Dict], city_name: str) -> None:
    """
    將數據處理和訊息回覆的邏輯封裝起來，避免在主函式中重複寫入。
    使用聚合好的數據建立一個 Flex Message；如果失敗則回退到發送一個簡單的文字訊息，確保用戶總能收到回覆。
    """
    # 數據不存在的錯誤處理
    if not all_weather_data:
        """
        檢查 `all_weather_data` 是否為空；如果為空，表示數據聚合過程失敗，程式不會建立 Flex Message，而是直接發送一個預先寫好的錯誤文字訊息。
        """
        message_text = f"抱歉，無法取得 {city_name} 的今日天氣資訊，請稍候再試。"
        send_line_reply_message(api, reply_token, [TextMessage(text=message_text)])
        logger.warning(f"未能為 {city_name} 建立今日天氣訊息，已發送文字備援。")
        return
        
    try:
        # 1. 建構 Flex Message
        """
        呼叫 `build_daily_weather_flex_message` 創建一個 Flex Message 物件。
        將聚合好的數據作為參數傳遞。
        """
        flex_message_to_send = build_daily_weather_flex_message(
            location=all_weather_data.get("locationName", city_name),
            parsed_weather=all_weather_data.get("general_forecast", {}),
            parsed_data=all_weather_data.get("hourly_forecast", []),
            parsed_uv_data=all_weather_data.get("uv_data", {})
        )

        # 確保返回的對象確實是 LINE SDK 的 FlexMessage 類型
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

# --- 處理「今日天氣」或城市名稱的訊息輸入 ---
def handle_today_message(api, event: MessageEvent) -> bool:
    """
    這個函式是今日天氣查詢流程的起點，根據用戶輸入的內容，決定要查詢哪個城市的天氣。
    呼叫輔助函式完成數據獲取、訊息建構和回覆的整個流程。
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 處理用戶輸入「今日天氣」這個關鍵字的邏輯
    if "今日天氣" in message_text:
        """
        從資料庫獲取用戶設定的預設城市；如果沒有設定，則使用一個硬編碼的預設城市（例如「臺中市」）。
        接著呼叫 `get_today_all_weather_data` 一次性獲取所有需要的數據。
        最後呼叫 `build_and_send_today_weather_message` 處理訊息的發送。
        """
        logger.info(f"用戶 {user_id} 查詢今日天氣。")

        user_city = get_default_city(user_id) # 獲取用戶的預設城市
        if not user_city:
            user_city = "臺中市" # 設定預設值
            logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{user_city}")

        # 1. 呼叫數據聚合器，一次性取得所有資料
        all_weather_data = get_today_all_weather_data(user_city)

        # 2. 建構並發送訊息
        build_and_send_today_weather_message(api, reply_token, all_weather_data, user_city)

        # 設定用戶狀態以供後續對話使用
        set_user_state(user_id, 'awaiting_today_city_input', data={'city': user_city})
        logger.info(f"已為用戶 {user_id} 設定狀態為 'awaiting_today_city_input'。")
    
    return True # 返回 True 表示此函式已處理該事件
    
# --- 根據特定城市抓今日 (36小時) 天氣預報資料、組 Flex、回覆 ---
def reply_today_weather_of_city(api, reply_token: str, user_id: str, city_name: str) -> None:
    """
    這個函式主要供其他模組呼叫，用於處理特定城市名稱的查詢。
    先對城市名稱進行正規化，然後呼叫 `get_today_all_weather_data` 獲取數據，並透過 `build_and_send_today_weather_message` 發送訊息。
    """
    normalized_city_name = normalize_city_name(city_name)
    logger.info(f"正在為用戶 {user_id} 查詢 {normalized_city_name} 的今日天氣預報。")

    # 1. 呼叫數據聚合器，一次性取得所有資料
    all_weather_data = get_today_all_weather_data(normalized_city_name)

    # 2. 建構並發送訊息
    build_and_send_today_weather_message(api, reply_token, all_weather_data, normalized_city_name)
    
    return False # 返回 `False`，讓事件可以被其他 handler 繼續處理