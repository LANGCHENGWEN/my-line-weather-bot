# handlers/text_router.py
"""
這個檔案是 LINE Bot 處理所有文字訊息的核心路由器。
它的主要職責是接收使用者傳來的文字訊息，並根據預先定義的優先級規則，將訊息分發給正確的處理函式。
路由的優先順序：
1. 忽略 Postback 副作用文字，避免重複處理。
2. 檢查訊息是否為精確匹配的「全局關鍵字」。
3. 檢查使用者是否處於特定的「狀態」（例如：正在等待城市輸入）。
4. 如果以上規則皆不匹配，則交由「預設處理器」處理。
這種層級分明的設計確保了每個訊息都能被正確且唯一的處理，避免邏輯混亂。
"""
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import get_user_state, clear_user_state

logger = logging.getLogger(__name__)

# --- 狀態 → handler ---
"""
定義使用者處於特定狀態時，應該將訊息導向哪個模組進行處理。
這是一種「狀態機」模式的實現。
當使用者點擊「查詢其他縣市」的按鈕，會將其狀態標記為 "awaiting_city_input"。
接下來使用者輸入的任何文字，都會被這個路由器優先導向到 `city_input_handler` 處理，而不是被其他關鍵字匹配所干擾，直到這個流程結束為止。
"""
DISPATCH_STATE = {
    "awaiting_default_city_input"  : "handlers.city_input_handler", # 等待輸入預設城市
    "awaiting_city_input"          : "handlers.city_input_handler", # 等待輸入查詢即時天氣其他縣市
    "awaiting_forecast_city_input" : "handlers.city_input_handler", # 等待輸入查詢未來預報其他縣市
    "awaiting_outfit_city_input"   : "handlers.city_input_handler", # 等待輸入查詢穿搭建議其他縣市
    "awaiting_today_city_input"    : "handlers.city_input_handler"
}

"""
這兩個字典定義了當使用者輸入精確的關鍵字時，應該將訊息導向到哪個模組和哪個函式進行處理。
允許機器人直接響應使用者輸入的特定指令。
這種模式是 `postback_router` 的文字版，提供使用者透過文字指令來觸發功能，並將關鍵字與處理邏輯分離，使程式碼更易於維護。
"""
# --- 關鍵字 → handler ---
DISPATCH_KEYWORD = {
    "即時天氣":"weather_current.current_handler",
    "未來預報":"weather_forecast.forecast_handler",
    "颱風現況":"typhoon.typhoon_handler",
    "地區影響預警":"typhoon.area_hazard_handler",
    "今日天氣":"weather_today.today_handler"
}

# --- 關鍵字 → 處理函式名稱 ---
DISPATCH_KEYWORD_HANDLERS = { # 這裡的處理函式名稱需和各個 handler.py 檔案中的函式名稱保持一致
    "即時天氣": "handle_current_message",
    "未來預報": "handle_forecast_message",
    "颱風現況": "handle_typhoon_message",
    "地區影響預警": "handle_area_hazard_message",
    "今日天氣": "handle_today_message"
}

# --- 忽略 Postback 文字的列表 ---
"""
LINE 的行為是當使用者點擊 Postback 按鈕時，Bot 會同時收到一個 PostbackEvent 和一個包含按鈕顯示文字的 MessageEvent。
為了避免機器人對同一個動作發送兩次回覆，這裡會列出所有 Rich Menu Postback 按鈕上的文字，並在收到這些文字訊息時，直接忽略不處理。
"""
POSTBACK_RELATED_TEXTS_TO_IGNORE = [
    "天氣查詢", "颱風專區", "生活提醒", "設定", "回首頁",
    "颱風路徑圖", "穿搭建議", "週末天氣", "節氣小知識",
    "每日天氣推播", "颱風通知推播", "週末天氣推播", "節氣小知識推播",
    "切換預設城市"
]

# --- 通用函式：安全的從指定模組中調用指定的處理函式 ---
def _call_handler(module_path: str, handler_name: str, api, event) -> bool:
    """
    用 `importlib` 在程式執行時動態載入模組，並使用 `getattr` 安全的取得對應的處理函式。
    這種動態調用機制可以避免在檔案開頭靜態的 import 所有處理函式，減少不必要的程式碼載入，讓路由器的程式碼更簡潔。
    `try...except` 區塊可以捕捉載入或呼叫函式時可能發生的錯誤，確保程式不會因為配置問題而崩潰。
    """
    try:
        mod = import_module(module_path)
        handler_func = getattr(mod, handler_name)
        
        logger.debug(f"導向至 {module_path}.{handler_name}")
        return handler_func(api, event)
    except (ImportError, AttributeError) as e:
        logger.error(f"無法調用處理函式 {handler_name}。模組或函式不存在: {e}")
        send_line_reply_message(api, event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部配置錯誤。")])
        clear_user_state(event.source.user_id)
        return False
    except Exception as e:
        logger.exception(f"調用處理函式 {handler_name} 時發生未預期錯誤: {e}")
        send_line_reply_message(api, event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍候再試。")])
        clear_user_state(event.source.user_id)
        return False

# --- 所有文字訊息的處理入口函式 ---
def handle(event):
    """
    按照預定義的優先級，將文字訊息分發給對應的處理模組。
    """
    user_id = event.source.user_id
    message_text = event.message.text # 取得使用者輸入的文字
    api = get_messaging_api()

    # 明確處理輸入縣市的情境
    user_state_info = get_user_state(user_id)
    state = user_state_info.get('state')

    logger.debug(f"路由器狀態 = {user_state_info} (user_id={user_id})")
    logger.debug(f"用戶輸入訊息: {message_text}")

    # --- 路由優先級邏輯 ---
    # 優先級 1：忽略 Postback 文字，避免重複回覆
    """
    當使用者點擊 Rich Menu 按鈕時，LINE 會發送一個 Postback 事件和一個文字訊息事件（文字內容就是按鈕上的文字）。
    Postback 事件會被 `postback_router` 處理，為了防止 `text_router` 再次處理這個文字訊息並發送重複的回覆，會在這裡檢查訊息內容，如果它與任何 Postback 按鈕的文字相同，就直接終止處理。
    """
    if message_text in POSTBACK_RELATED_TEXTS_TO_IGNORE:
        logger.info(f"[TextRouter] 偵測到 Postback 相關文字 '{message_text}'，由 TextRouter 忽略以避免重複回覆。")
        return # 直接返回，不進行後續處理，因為 Postback 事件已經被 postback_router 處理
    
    # 優先級 2：處理精確匹配的「全局關鍵字」
    """
    處理使用者直接輸入的關鍵字指令，例如「即時天氣」。
    這裡會根據 `DISPATCH_KEYWORD` 和 `DISPATCH_KEYWORD_HANDLERS` 字典，找到對應的模組和函式名稱，並使用 `_call_handler` 來動態執行。
    這種設計可以讓使用者直接跳過 Rich Menu，快速達到目的。
    """
    if message_text in DISPATCH_KEYWORD:
        module_path = DISPATCH_KEYWORD[message_text]
        handler_name = DISPATCH_KEYWORD_HANDLERS.get(message_text)
    
        if handler_name:
            logger.info(f"偵測到精確匹配關鍵字 '{message_text}'，導向至 {module_path}.{handler_name}。")
            _call_handler(module_path, handler_name, api, event)
            return
        else:
            logger.error(f"關鍵字 '{message_text}' 沒有對應的處理函式名稱。")
            _call_handler("handlers.default", "handle", api, event)
            return

    # 優先級 3：優先處理使用者處於特定「狀態」下的輸入
    """
    這是處理 `Postback` 之後的「文字輸入」的核心邏輯。
    確保當使用者處於特定狀態時（例如被要求輸入城市名稱），機器人的反應會按照預期的流程進行，而不會被其他的關鍵字或預設處理器干擾。
    這種狀態優先的設計，使得 Bot 的對話流程能夠更加清晰和可控。
    """
    if state in DISPATCH_STATE:
        module_path = DISPATCH_STATE[state]
        handler_name = f"handle_{state}"
        logger.info(f"依照用戶狀態 '{state}' 導向至 {module_path}.{handler_name}。")
        _call_handler(module_path, handler_name, api, event)
        return

    # 優先級 4：最低優先級 - 導向至預設處理器
    """
    這是路由器的最後一道防線。
    如果一個文字訊息不屬於上述任何一種情況（不是 Postback 相關、不是關鍵字、也沒有特定狀態），路由器會將其導向 `handlers.default` 模組。
    確保所有無法識別的文字訊息都能得到一個友善的「不明白」回覆，避免機器人保持沉默，同時也能處理通用的問候語等非指令性訊息。
    """
    logger.info("未匹配任何特定規則，導向至最終處理模組: handlers.default。")
    _call_handler("handlers.default", "handle", api, event)