# handlers/text_router.py
# from utils.api_helper import get_api
from importlib import import_module
from utils.api_helper import get_messaging_api
from utils.user_data_manager import get_user_state
from menu_handlers.menu_switcher import handle_menu_switching as switch

# 狀態 → handler
DISPATCH_STATE = {
    "awaiting_default_city_input": "handlers.default_city_input",
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
        1. handle_current_message(api, event)
        2. handle_forecast_message(api, event)
        3. handle(api, event)
        4. handle(event)          ← 最後的舊版相容
    """
    mod = import_module(module_path)
    api = get_messaging_api()         # 只有在真正需要時才取

    # 順序依序判斷
    if hasattr(mod, "handle_current_message"):
        return mod.handle_current_message(api, event)
    if hasattr(mod, "handle_forecast_message"):
        return mod.handle_forecast_message(api, event)
    if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
        return mod.handle(api, event)
    if hasattr(mod, "handle"):
        return mod.handle(event)

    # 都沒有就 raise（代表子模組寫得不對）
    raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

def handle(event):
    # 1) 依使用者 state 轉發
    state = get_user_state(event.source.user_id)
    if state and state in DISPATCH_STATE:
        import_module(DISPATCH_STATE[state]).handle(event)
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