# handlers/text_router.py
# 主要文字訊息分發器，負責接收所有來自使用者的文字訊息
# from utils.api_helper import get_api
import logging
from importlib import import_module

from utils.api_helper import get_messaging_api
from utils.user_data_manager import get_user_state
# from menu_handlers.menu_switcher import handle_menu_switching as switch

logger = logging.getLogger(__name__)

# 狀態 → handler
DISPATCH_STATE = {
    "awaiting_default_city_input": "handlers.default_city_input", # 等待輸入預設城市
    "awaiting_city_input":         "handlers.default_city_input", # 等待輸入查詢即時天氣其他縣市
    "awaiting_forecast_city_input":"handlers.default_city_input"  # 等待輸入查詢未來預報其他縣市
    # "awaiting_township_input": "weather_forecast.forecast_handler", # 等待輸入鄉鎮市區
    # "awaiting_full_location":  "weather_forecast.forecast_handler"  # 等待輸入縣市+鄉鎮市區
}

# 關鍵字 → handler
DISPATCH_KEYWORD = {
    "即時天氣":  "weather_current.current_handler",
    "未來預報":  "weather_forecast.forecast_handler",
    "颱風現況":      "typhoon.typhoon_handler",
    "穿搭":      "life_style.outfit_handler"
    # …
}

POSTBACK_RELATED_TEXTS_TO_IGNORE = [
    "天氣查詢",
    "颱風專區",        # 如果有這個子選單入口
    "生活提醒",        # 如果有這個子選單入口
    "設定",
    "回上一頁",
    "颱風路徑圖",      # 如果是 Postback 按鈕的顯示文字
    "每日提醒推播",
    "颱風通知推播",
    "週末天氣推播",
    "節氣小知識推播",
    "切換預設城市"    # 如果是 Postback 按鈕的顯示文字
    # ... 請根據你的所有 Rich Menu Postback 按鈕的 'label' (顯示文字) 來補充這個列表
]

def _dispatch_to_module(module_path: str, event, user_state_info: dict):
    """
    根據子模組提供的函式名稱，決定要傳哪些參數進去。
    預設支援的函式名稱（依優先順序）：
        1. handle_awaiting_..._input(api, event)  <-- 優先處理狀態相關輸入
        2. handle_current_message(api, event)
        3. handle_forecast_message(api, event)
        4. handle(api, event)
        5. handle(event)          ← 最後的舊版相容
    """
    mod = import_module(module_path)
    api = get_messaging_api()         # 只有在真正需要時才取
    state = user_state_info.get('state', 'idle')
    
    """
    if hasattr(mod, "handle_township_input"):
        result = mod.handle_township_input(api, event)
        if result:
            return result
    """

    # 1. 優先匹配狀態相關的處理函式 (通常用於接收用戶輸入特定數據，如城市名)
    if state == "awaiting_forecast_city_input" and hasattr(mod, "handle_awaiting_forecast_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_forecast_city_input for state: {state}")
        # 假設 handle_awaiting_forecast_city_input 會發送訊息並返回 True/False 或直接 None
        return mod.handle_awaiting_forecast_city_input(api, event)
    elif state == "awaiting_city_input" and hasattr(mod, "handle_awaiting_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_city_input for state: {state}")
        return mod.handle_awaiting_city_input(api, event)
    elif state == "awaiting_default_city_input" and hasattr(mod, "handle_awaiting_default_city_input"):
        logger.debug(f"導向至 handle_awaiting_default_city_input for state: {state}")
        return mod.handle_awaiting_default_city_input(api, event)
    
    # 2. 其次匹配特定功能的處理函式 (通用關鍵字可能導向這些)
    if hasattr(mod, "handle_current_message"):
        logger.debug(f"導向至 handle_current_message")
        return mod.handle_current_message(api, event)
    if hasattr(mod, "handle_forecast_message"):
        logger.debug(f"導向至 handle_forecast_message")
        return mod.handle_forecast_message(api, event)
    if hasattr(mod, "handle_typhoon_message"):
        logger.debug(f"導向至 handle_typhoon_message")
        return mod.handle_typhoon_message(api, event)
    
    # 3. Fallback 到通用的 handle 函式
    if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
        logger.debug(f"導向至 handle(api, event)")
        return mod.handle(api, event)
    if hasattr(mod, "handle"):
        logger.debug(f"導向至 handle(event)")
        return mod.handle(event)
    
    # 如果都沒有匹配到，則拋出錯誤
    raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

# --- 主入口函式 ---
def handle(event):
    """
    文字訊息路由的主要入口。
    按照預定義的優先級順序分發文字訊息。
    """
    user_id = event.source.user_id
    message_text = event.message.text # 取得用戶輸入的文字

    # 明確處理輸入縣市的情境
    user_state_info = get_user_state(user_id)
    state = user_state_info.get('state', 'idle')

    logger.debug(f"路由器狀態 = {get_user_state(user_id)} (user_id={user_id})")
    logger.debug(f"用戶輸入訊息: {message_text}")

    # --- 路由優先級邏輯 ---
    # 1. 檢查是否為 Postback 副作用文字，如果是則直接忽略 (最高優先級)
    if message_text in POSTBACK_RELATED_TEXTS_TO_IGNORE:
        logger.info(f"[TextRouter] 偵測到 Postback 相關文字 '{message_text}'，由 TextRouter 忽略以避免重複回覆。")
        return # 直接返回，不進行後續處理
    
    # 2. 處理用戶處於特定「狀態」下的輸入 (例如：正在等待用戶輸入城市名稱)
    if state and state in DISPATCH_STATE:
        logger.info(f"[TextRouter] 依照用戶狀態 '{state}' 導向處理模組: {DISPATCH_STATE[state]}。")
        handled = _dispatch_to_module(DISPATCH_STATE[state], event, user_state_info)
        if handled: # 如果狀態處理器已處理並回覆，就結束
            return
        
    # 3. 處理精確匹配的「全局關鍵字」 (例如：Rich Menu 按鈕的文本，或用戶直接輸入的指令)
    if message_text in DISPATCH_KEYWORD:
        module = DISPATCH_KEYWORD[message_text]
        logger.info(f"[TextRouter] 偵測到精確匹配關鍵字 '{message_text}'，導向至 {module}。")
        _dispatch_to_module(module, event, user_state_info)
        return
    
    logger.info(f"[TextRouter] 未匹配任何特定規則，導向至最終處理模組: handlers.default。")
    _dispatch_to_module("handlers.default", event, user_state_info)

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