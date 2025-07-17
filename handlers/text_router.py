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

    # 順序依序判斷其他非狀態特定的函式
    if hasattr(mod, "handle_current_message"):
        logger.debug(f"導向至 handle_current_message")
        return mod.handle_current_message(api, event)
    if hasattr(mod, "handle_forecast_message"):
        logger.debug(f"導向至 handle_forecast_message")
        return mod.handle_forecast_message(api, event)

    # 明確處理輸入縣市的情境
    state = get_user_state(event.source.user_id) # 在這裡取得狀態，以便前面判斷
    
    """
    if hasattr(mod, "handle_township_input"):
        result = mod.handle_township_input(api, event)
        if result:
            return result
    """

    # ⚠️ 這裡進行修改：將處理狀態相關輸入的邏輯移到最前面
    if state == "awaiting_forecast_city_input" and hasattr(mod, "handle_awaiting_forecast_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_forecast_city_input for state: {state}")
        return mod.handle_awaiting_forecast_city_input(api, event)
    elif state == "awaiting_city_input" and hasattr(mod, "handle_awaiting_city_input"):          # 查詢其他縣市 default_city_input.py
        logger.debug(f"導向至 handle_awaiting_city_input for state: {state}")
        return mod.handle_awaiting_city_input(api, event)
    elif state == "awaiting_default_city_input" and hasattr(mod, "handle_awaiting_default_city_input"):
        logger.debug(f"導向至 handle_awaiting_default_city_input for state: {state}")
        return mod.handle_awaiting_default_city_input(api, event)
    
    # fallback: 一般訊息處理
    if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
        logger.debug(f"導向至 handle(api, event)")
        return mod.handle(api, event)
    if hasattr(mod, "handle"):
        logger.debug(f"導向至 handle(event)")
        return mod.handle(event)
    raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

def handle(event):
    # 1) 依使用者 state 轉發
    state = get_user_state(event.source.user_id)
    logger.debug(f"路由器狀態 = {state} (user_id={event.source.user_id})")

    # 1. 依照狀態處理
    if state and state in DISPATCH_STATE:
        handled = _dispatch_to_module(DISPATCH_STATE[state], event)
        # import_module(DISPATCH_STATE[state]).handle(event)
        if handled:
            return

    # 2) Rich‑menu 切換
    line_bot_api = get_messaging_api() # 拿到 MessagingApi 實例
    if switch(event, line_bot_api):    # 傳入第二個參數 line_bot_api
        return

    # 3) 依關鍵字轉發；找不到就交給 handlers.default
    key = next((k for k in DISPATCH_KEYWORD if k in event.message.text), None)
    module = DISPATCH_KEYWORD.get(key, "handlers.default")
    
    # 交給小工具判斷該用哪個函式
    _dispatch_to_module(module, event)