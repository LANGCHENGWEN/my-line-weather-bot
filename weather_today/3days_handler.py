# weather_today/3days_handler.py
# 主要處理即時天氣用戶輸入的回覆邏輯
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import MessageEvent

# 從您的設定檔中導入 API 金鑰
from config import CWA_API_KEY

from utils.message_builder import format_flex_message # 用於將 Flex JSON 轉換為 Line SDK 物件
from utils.text_processing import normalize_city_name

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import (
    send_line_reply_message, send_api_error_message
)

# 導入今天天氣相關的模組
from .cwa_3days_api import get_cwa_today_data
from .weather_today_parser import parse_today_weather
from .today_weather_flex_messages import build_today_weather_flex

# 導入用戶數據管理器 (用於獲取用戶預設城市)
from utils.user_data_manager import get_default_city

logger = logging.getLogger(__name__)

def handle_today_message(messaging_api, event: MessageEvent) -> bool:
    """
    處理「今日天氣」的訊息輸入。
    如果訊息被處理，則返回 True，否則返回 False。
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的訊息: {message_text}")

    # 檢查是否包含「今日天氣」關鍵字
    if "今日天氣" in message_text:
        logger.info(f"用戶 {user_id} 查詢今日天氣。")

        # 獲取用戶的預設城市 (假設已經設定好，如果沒有則使用預設值)
        # 您需要確保 get_default_city 函數能正確返回城市名稱
        user_city = get_default_city(user_id)
        if not user_city:
            user_city = "臺中市" # 這裡可以設定一個最常用的預設城市
            logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{user_city}")

        # 1. 取得原始天氣數據
        today_data = get_cwa_today_data(CWA_API_KEY, user_city)

        if not today_data:
            logger.error(f"無法取得中央氣象署 F-C0032-001 {user_city} 的資料。")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text=f"抱歉，無法取得 {user_city} 的今日天氣資料，請稍候再試。")])
            return True

        # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
        parsed_today_weather = parse_today_weather(today_data, user_city)

        if not parsed_today_weather:
            logger.error(f"無法從取得的 F-C0032-001 資料中解析 {user_city} 的今日天氣資訊。")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text=f"抱歉，無法解析 {user_city} 的今日天氣資訊。")])
            return True
        
        # 3. 將格式化後的數據填充到 Flex Message 模板中 (得到 Flex Message 的字典結構)
        flex_json_content = build_today_weather_flex(parsed_today_weather)

        if not flex_json_content:
            logger.error(f"格式化今日天氣 Flex Message 失敗。")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text=f"抱歉，無法顯示 {user_city} 的今日天氣卡片。")])
            return True
        
        # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
        # 使用 line_common_messaging 中的 format_flex_message 函數
        flex_msg_object = format_flex_message(f"{user_city} 今日天氣", flex_json_content)

        # 額外檢查：format_flex_message 也可能返回 TextMessage (降級處理)
        if isinstance(flex_msg_object, TextMessage):
            send_line_reply_message(messaging_api, reply_token, [flex_msg_object])
            return True

        # 5. 發送回覆訊息
        send_line_reply_message(messaging_api, reply_token, [flex_msg_object])
        logger.info(f"已向用戶 {user_id} 發送 {user_city} 今日天氣 Flex Message。")
        return True
    
    # --- 通用回覆函式：今日天氣預報 (F-C0032-001 - 今明36小時) ---
def reply_today_weather_of_city(api, reply_token: str, city_name: str) -> None:
    """
    直接根據 city_name 抓今日 (36小時) 天氣預報資料、組 Flex、回覆。
    """
    normalized_city_name = normalize_city_name(city_name)
    logger.info(f"正在查詢 {normalized_city_name} 的今日天氣預報。")

    # 1. 取資料 (使用 F-C0032-001 的 API 和 Parser)
    raw = get_cwa_today_data(CWA_API_KEY, normalized_city_name)
    if not raw:
        logger.error(f"無法取得 {normalized_city_name} 的今日天氣預報資料。")
        send_api_error_message(api, None, reply_token, normalized_city_name)
        return

    # 2. 解析
    parsed = parse_today_weather(raw, normalized_city_name)
    if not parsed:
        logger.error(f"無法解析 {normalized_city_name} 的今日天氣預報資訊。")
        send_api_error_message(api, None, reply_token, normalized_city_name)
        return

    # 3. build flex json → FlexMessage
    flex_json = build_today_weather_flex(parsed)
    flex_msg = format_flex_message(f"{normalized_city_name} 今日天氣預報", flex_json)

    # 4. 回覆
    send_line_reply_message(api, reply_token, [flex_msg])
    logger.info(f"已回覆 {normalized_city_name} 的今日天氣預報。")
    
    return False # 這個 handler 沒有處理這個訊息