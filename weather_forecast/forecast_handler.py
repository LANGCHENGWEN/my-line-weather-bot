# forecast_handler.py
# 主要處理天氣預報用戶輸入的回覆邏輯
import logging
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import MessageEvent
# from linebot.v3.models import PostbackAction # 引入 PostbackAction

# 載入預報天氣相關功能
# from .welcome_flex import create_welcome_flex_message
from .forecast_options_flex import create_forecast_options_flex_message
# from .cwa_forecast_api import get_cwa_forecast_data
# from .weather_forecast_parser import parse_forecast_weather
# from .line_forecast_messaging import format_forecast_weather_message # 只導入 forecast 的格式化
# from .welcome_flex import create_welcome_flex_message

# 載入通用訊息發送功能 (如果新增了 line_common_messaging.py，這裡就從那裡導入)
from utils.line_common_messaging import send_line_reply_message

# 載入使用者狀態管理器
from utils.user_data_manager import (
    get_user_state, set_user_state,
    get_default_city, clear_user_state, is_valid_city
)

logger = logging.getLogger(__name__)

# 在 handlers.py 裡面需要有 line_bot_api 的實例來發送訊息
# 這個應該在 initialize_handlers 裡面傳入
'''
def initialize_handlers(line_bot_api_instance, handler_instance):
    """
    初始化 handlers 模組，傳遞 LineBotApiExt 和 WebhookHandler 實例。
    """
    global _line_bot_api, _handler
    _line_bot_api = line_bot_api_instance
    _handler = handler_instance
    logger.info("Handlers 模組已初始化。")

    _handler.add(MessageEvent, message=TextMessage)(handle_message)
    logger.info("訊息事件處理器已註冊。")
'''
def normalize_city_name(city_name: str) -> str:
    """
    將常見的縣市名稱替換為標準格式，例如把「台」改成「臺」。
    """
    if not city_name:
        return city_name
    return city_name.replace("台", "臺")

def handle_forecast_message(messaging_api, event: MessageEvent) -> bool:
    """
    處理與天氣預報相關的文字訊息。
    根據使用者當前狀態或訊息內容，回覆第一個選單或處理鄉鎮市區輸入。
    如果訊息被此 handler 處理，則返回 True，否則返回 False。
    """
    user_id = event.source.user_id # 獲取 user_id
    message_text = event.message.text
    reply_token = event.reply_token
    # user_current_state = get_user_state(user_id)

    # logger.info(f"從用戶 {user_id} 收到文字訊息: '{message_text}', 當前狀態: {user_current_state}")

    # 1. 處理啟動天氣查詢的關鍵字 (例如使用者輸入 "未來預報" 或 "天氣")
    if message_text == "未來預報":
        default_city = get_default_city(user_id) or "臺中市"
        default_city = normalize_city_name(default_city)  # 字串轉換
        
        flex_message = create_forecast_options_flex_message(default_city)
        # 修改這裡，傳入 user_id
        send_line_reply_message(messaging_api, reply_token, [flex_message])
        logger.info(f"用戶 {user_id} 請求未來預報，已回覆天數選單。")

        # set_user_state(user_id, "awaiting_township_input")
        return True
    
'''    
def handle_township_input(messaging_api, event):
    """處理「輸入鄉鎮市區 或 縣市+鄉鎮市區」兩種情況"""
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    state = get_user_state(user_id)
    # 2. 處理使用者輸入鄉鎮市區 (在 "awaiting_township_input" 狀態下)
    # 這是使用者看到第一個選單後，輸入鄉鎮市區名稱的環節
    if state == "awaiting_township_input":
        default_city = get_default_city(user_id) or "臺中市"
        township = message_text

        flex = create_forecast_options_flex_message(default_city, township)
        send_line_reply_message(messaging_api, reply_token, [flex])

        # 這裡可以加入鄉鎮市區的有效性檢查，例如查詢資料庫
        # 為了簡潔，這裡直接使用輸入的鄉鎮市區
        clear_user_state(user_id)
        logger.info(f"{user_id} 查詢 {default_city}{township} 預報，已回覆天數選單")
        return True # 表示此 handler 已處理此訊息
    
    # 3. 處理使用者直接輸入「縣市+鄉鎮市區」的邏輯 (如果「查詢其他縣市+鄉鎮市區」按鈕被點擊過，且用戶直接輸入)
    elif state == "awaiting_full_location":
        default_city, township = _parse_full_location(message_text)

        if default_city and township and is_valid_city(default_city):
            flex = create_forecast_options_flex_message(default_city, township)
            send_line_reply_message(messaging_api, reply_token, [flex])

            clear_user_state(user_id)
            logger.info(f"{user_id} 查詢 {default_city}{township} 預報，已回覆天數選單")
        else:
            send_line_reply_message(
                messaging_api,
                reply_token,
                [TextMessage(text="請用「縣市+鄉鎮市區」格式，例如：台北市信義區")],
            )
            logger.warning(f"{user_id} 輸入格式不對：{message_text}")
        return True
    
    # 其他狀況不處理
    return False
'''
'''
# 小工具：從「臺中市北區」解析出 (縣市, 鄉鎮市區)
def _parse_full_location(message: str) -> tuple[str | None, str | None]:
    for token in ("市", "縣"):
        if token in message:
            default_city, township = message.split(token, 1)
            default_city += token
            township = township.strip()
            return default_city, township or None
    return None, None
'''

'''
        # 嘗試解析 "縣市+鄉鎮市區" 格式
        parsed_county = None
        parsed_township = None
        
        # 簡易解析：假設格式為 "臺北市信義區" 或 "高雄市鼓山區"
        # 這是一個非常基礎的解析器，實際應用中建議使用更強健的地理編碼或預定義地點列表。
        if "市" in message_text:
            parts = message_text.split("市", 1)
            parsed_county = parts[0] + "市"
            if len(parts) > 1:
                parsed_township = parts[1]
        elif "縣" in message_text:
            parts = message_text.split("縣", 1)
            parsed_county = parts[0] + "縣"
            if len(parts) > 1:
                parsed_township = parts[1]

        if parsed_county and parsed_township:
            clear_user_state(user_id) # 清除狀態
            # 直接回覆天數選擇選單
            flex_message = create_forecast_options_flex_message(parsed_county, parsed_township)
            send_line_reply_message(messaging_api, reply_token, [flex_message])
            logger.info(f"用戶 {user_id} 直接輸入完整地點 '{parsed_county}{parsed_township}'，已回覆天數選單。")
            return True
        else:
            send_line_reply_message(
                messaging_api, reply_token, 
                [TextMessage(text="抱歉，無法識別您輸入的縣市+鄉鎮市區格式，請重新輸入，例如：臺北市信義區。")]
            )
            logger.warning(f"用戶 {user_id} 輸入的完整地點格式不正確: '{message_text}'")
            return True # 雖然格式不對，但我們處理了這個意圖

    # 如果沒有上述任何條件符合，則此 handler 不處理此訊息
    logger.debug(f"forecast_handler 未處理訊息: '{message_text}'，將傳遞給下一個 handler。")
    return False # 如果沒有上述任何條件符合，則此 handler 不處理此訊息

logger.info("forecast_handler.py 模組已載入。")
'''