# handlers/text_router.py
# from utils.api_helper import get_api
import logging
from importlib import import_module

from utils.api_helper import get_messaging_api
from utils.user_data_manager import get_user_state
from menu_handlers.menu_switcher import handle_menu_switching as switch

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
    "颱風":      "weather_typhoon.typhoon_handler",
    "穿搭":      "life_style.outfit_handler"
    # …
}

def _dispatch_to_module(module_path: str, event):
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

    # 明確處理輸入縣市的情境
    user_state_info = get_user_state(event.source.user_id)
    state = user_state_info.get('state', 'idle') # 在這裡取得狀態，以便前面判斷
    
    """
    if hasattr(mod, "handle_township_input"):
        result = mod.handle_township_input(api, event)
        if result:
            return result
    """

    # ⚠️ 這裡進行修改：將處理狀態相關輸入的邏輯移到最前面
    if state == "awaiting_forecast_city_input" and hasattr(mod, "handle_awaiting_forecast_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_forecast_city_input for state: {state}")
        # 假設 handle_awaiting_forecast_city_input 會發送訊息並返回 True/False 或直接 None
        result = mod.handle_awaiting_forecast_city_input(api, event)
        if result: # 如果這個 handler 已經處理並回覆了，就結束
            return True # 返回 True 表示這個事件已經被處理
    elif state == "awaiting_city_input" and hasattr(mod, "handle_awaiting_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_city_input for state: {state}")
        result = mod.handle_awaiting_city_input(api, event)
        if result: # 如果這個 handler 已經處理並回覆了，就結束
            return True # 返回 True 表示這個事件已經被處理
    elif state == "awaiting_default_city_input" and hasattr(mod, "handle_awaiting_default_city_input"):
        logger.debug(f"導向至 handle_awaiting_default_city_input for state: {state}")
        result = mod.handle_awaiting_default_city_input(api, event)
        if result: # 如果這個 handler 已經處理並回覆了，就結束
            return True # 返回 True 表示這個事件已經被處理
    
    # 順序依序判斷其他非狀態特定的函式
    if hasattr(mod, "handle_current_message"):
        logger.debug(f"導向至 handle_current_message")
        return mod.handle_current_message(api, event)
    if hasattr(mod, "handle_forecast_message"):
        logger.debug(f"導向至 handle_forecast_message")
        return mod.handle_forecast_message(api, event)
    
    # fallback: 一般訊息處理
    if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
        logger.debug(f"導向至 handle(api, event)")
        return mod.handle(api, event)
    if hasattr(mod, "handle"):
        logger.debug(f"導向至 handle(event)")
        return mod.handle(event)
    
    # 如果都沒有匹配到，則拋出錯誤
    raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

def handle(event):
    user_id = event.source.user_id
    message_text = event.message.text # 取得用戶輸入的文字
    logger.debug(f"路由器狀態 = {get_user_state(user_id)} (user_id={user_id})")
    logger.debug(f"用戶輸入訊息: {message_text}")

    # 1) 依使用者 state 轉發
    
    # logger.debug(f"路由器狀態 = {state} (user_id={event.source.user_id})")

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

    # 2) Rich‑menu 切換
    line_bot_api = get_messaging_api() # 拿到 MessagingApi 實例
    if switch(event, line_bot_api):    # 傳入第二個參數 line_bot_api
        logger.debug(f"偵測到 Rich Menu 切換動作。")
        return

    # 3) 依關鍵字轉發；找不到就交給 handlers.default
    key = next((k for k in DISPATCH_KEYWORD if k in message_text), None)
    module = DISPATCH_KEYWORD.get(key, "handlers.default")
    
    logger.debug(f"導向至最終處理模組: {module}")
    # 交給小工具判斷該用哪個函式
    _dispatch_to_module(module, event)