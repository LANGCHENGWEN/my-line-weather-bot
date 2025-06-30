# handlers/text_router.py
# from utils.api_helper import get_api
from importlib import import_module
from user_data_manager import get_user_state
from menu_handlers.menu_switcher import handle_menu_switching as switch
from utils.api_helper import get_messaging_api

# 狀態 → handler
DISPATCH_STATE = {
    "awaiting_default_city_input": "handlers.default_city_input",
}

# 關鍵字 → handler
DISPATCH_KEYWORD = {
    "即時天氣":  "handlers.menu_weather",
    "未來預報":  "handlers.menu_weather",
    "颱風":      "handlers.menu_typhoon",
    "穿搭":      "handlers.menu_life",
    # …
}

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
    import_module(module).handle(event)