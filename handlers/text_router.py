# handlers/text_router.py
# 主要文字訊息分發器，負責接收所有來自使用者的文字訊息
# from utils.api_helper import get_api
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message # 引入共用訊息發送函式
from utils.user_data_manager import get_user_state, clear_user_state
# from menu_handlers.menu_switcher import handle_menu_switching as switch

logger = logging.getLogger(__name__)

# 狀態 → handler
DISPATCH_STATE = {
    "awaiting_default_city_input"  : "handlers.city_input_handler", # 等待輸入預設城市
    "awaiting_city_input"          : "handlers.city_input_handler", # 等待輸入查詢即時天氣其他縣市
    "awaiting_forecast_city_input" : "handlers.city_input_handler", # 等待輸入查詢未來預報其他縣市
    "awaiting_outfit_city_input"   : "handlers.city_input_handler", # 等待輸入查詢穿搭建議其他縣市
    "awaiting_today_city_input"    : "handlers.city_input_handler"
    # "awaiting_township_input": "weather_forecast.forecast_handler", # 等待輸入鄉鎮市區
    # "awaiting_full_location":  "weather_forecast.forecast_handler"  # 等待輸入縣市+鄉鎮市區
}

# 關鍵字 → handler
DISPATCH_KEYWORD = {
    "即時天氣":"weather_current.current_handler",
    "未來預報":"weather_forecast.forecast_handler",
    "颱風現況":"typhoon.typhoon_handler",
    "地區影響預警":"typhoon.area_hazard_handler",
    "今日天氣":"weather_today.today_handler"
    # …
}

# 關鍵字 → 處理函式名稱 (新增這個字典)
DISPATCH_KEYWORD_HANDLERS = {
    "即時天氣": "handle_current_message", # 注意這裡，如果是處理「即時天氣」
    "未來預報": "handle_forecast_message",
    "颱風現況": "handle_typhoon_message",
    "地區影響預警": "handle_area_hazard_message",
    "今日天氣": "handle_today_message", # <-- 這裡，對應到 today_handler.py 中的函式名稱
}

POSTBACK_RELATED_TEXTS_TO_IGNORE = [
    "天氣查詢", "颱風專區", "生活提醒", "設定", "回上一頁",
    "颱風路徑圖", "穿搭建議", "週末天氣", "節氣小知識",
    "每日提醒推播", "颱風通知推播", "週末天氣推播", "節氣小知識推播",
    "切換預設城市"    # 如果是 Postback 按鈕的顯示文字
    # ... 請根據你的所有 Rich Menu Postback 按鈕的 'label' (顯示文字) 來補充這個列表
]

def _call_handler(module_path: str, handler_name: str, api, event) -> bool:
    """
    通用函式：安全地從指定模組中調用指定的處理函式。
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

# --- 主入口函式 ---
def handle(event):
    """
    文字訊息路由的主要入口。
    按照預定義的優先級順序分發文字訊息。
    """
    user_id = event.source.user_id
    message_text = event.message.text # 取得用戶輸入的文字
    api = get_messaging_api()

    # 明確處理輸入縣市的情境
    user_state_info = get_user_state(user_id)
    state = user_state_info.get('state')

    logger.debug(f"路由器狀態 = {user_state_info} (user_id={user_id})")
    logger.debug(f"用戶輸入訊息: {message_text}")

    # --- 路由優先級邏輯 ---
    # 1. 最高優先級：檢查是否為 Postback 副作用文字，如果是則直接忽略
    if message_text in POSTBACK_RELATED_TEXTS_TO_IGNORE:
        logger.info(f"[TextRouter] 偵測到 Postback 相關文字 '{message_text}'，由 TextRouter 忽略以避免重複回覆。")
        return # 直接返回，不進行後續處理，因為 Postback 事件已經被 postback_router 處理
    
    # 2. 第二優先級：處理精確匹配的「全局關鍵字」
    if message_text in DISPATCH_KEYWORD:
        module_path = DISPATCH_KEYWORD[message_text]
        # 這裡的處理函式名稱需和各個 handler.py 檔案中的函式名保持一致
        handler_name = DISPATCH_KEYWORD_HANDLERS.get(message_text)
    
        if handler_name:
            logger.info(f"偵測到精確匹配關鍵字 '{message_text}'，導向至 {module_path}.{handler_name}。")
            _call_handler(module_path, handler_name, api, event)
            return
        else:
            logger.error(f"關鍵字 '{message_text}' 沒有對應的處理函式名稱。")
            _call_handler("handlers.default", "handle", api, event)
            return

    # 3. 第三優先級：優先處理用戶處於特定「狀態」下的輸入
    if state in DISPATCH_STATE:
        module_path = DISPATCH_STATE[state]
        handler_name = f"handle_{state}"
        logger.info(f"依照用戶狀態 '{state}' 導向至 {module_path}.{handler_name}。")
        _call_handler(module_path, handler_name, api, event)
        return

    # 4. 最低優先級：如果以上皆不匹配，則導向至預設處理器
    logger.info("未匹配任何特定規則，導向至最終處理模組: handlers.default。")
    _call_handler("handlers.default", "handle", api, event)

    """
    # 1. 優先處理高優先級的「關鍵字」命令，無論當前狀態為何
    #    這包括從 Rich Menu 點擊的「即時天氣」等
    if message_text in DISPATCH_KEYWORD:
        module = DISPATCH_KEYWORD[message_text]
        logger.debug(f"偵測到高優先級關鍵字 '{message_text}'，導向至 {module}")
        _dispatch_to_module(module, event)
        return # 處理完畢，直接返回，不再進行後續判斷

    # 2. 依使用者 state 轉發（如果沒有高優先級關鍵字觸發）
    user_state_info = get_user_state(event.source.user_id)
    state = user_state_info.get('state', 'idle')
    if state and state in DISPATCH_STATE:
        logger.debug(f"依照用戶狀態 '{state}' 導向處理。")
        handled = _dispatch_to_module(DISPATCH_STATE[state], event)
        # import_module(DISPATCH_STATE[state]).handle(event)
        if handled:
            return # 如果狀態處理器已處理並回覆，就結束

    # 3) 依關鍵字轉發；找不到就交給 handlers.default
    key = next((k for k in DISPATCH_KEYWORD if k in message_text), None)
    module = DISPATCH_KEYWORD.get(key, "handlers.default")
    
    logger.debug(f"導向至最終處理模組: {module}")
    # 交給小工具判斷該用哪個函式
    _dispatch_to_module(module, event)
    """