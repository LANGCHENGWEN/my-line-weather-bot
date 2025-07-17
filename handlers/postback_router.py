# handlers/postback_router.py
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.user_data_manager import set_user_state
from utils.line_common_messaging import send_line_reply_message

from handlers import postback_weather
from menu_handlers.menu_switcher import switch_to_alias

'''
from weather_current import current_handler
from weather_typhoon import typhoon_handler
from life_style import reminder_handler
from menu_handlers import settings_menu_handler
'''

logger = logging.getLogger(__name__)

# -------------------- 1) Rich‑menu 別名對照 --------------------
# alias 需與 rich_menu_configs.py 及 JSON 別名一致
ACTION_TO_ALIAS = {
    "weather_query"       : "weather_query_alias",
    "typhoon_area"        : "typhoon_zone_alias",
    "lifestyle_reminders" : "life_reminder_alias",
    "settings"            : "settings_alias",
}

# 所有 action 與「子 handler 模組路徑」的對照
ACTION_DISPATCH = {
    "weather_query"      : "weather_current.current_handler",
    "get_weather"        : "weather_forecast.postback_handler",
    "typhoon_area"       : "weather_typhoon.typhoon_handler",
    "lifestyle_reminders": "life_style.reminder_handler",
    "settings"           : "menu_handlers.settings_menu_handler",
}

# -------------------- 3) 入口 --------------------
def handle(event):
    """
    收到 PostbackEvent 之後：
      ① 解析 action
      ② 先切換 Rich‑menu (如果對應得到 alias)
      ③ 再看有沒有對應 handler，要就呼叫
      ④ 都沒有就回覆「不明白」
    """
    api = get_messaging_api()
    data = parse_qs(event.postback.data)
    action = data.get("action", [""])[0]
    user_id = event.source.user_id

    # 先判斷 change_city
    if action == "change_city":
        return postback_weather.handle(event)
    
    # 判斷 forecast_other_city
    if action == "forecast_other_city":
        return postback_weather.handle(event)

    # ---------- (A) 切換 Rich‑menu ----------
    alias = ACTION_TO_ALIAS.get(action)
    if alias:
        # switch_to_alias 需在 menu_switcher 裡面封裝 link_rich_menu_id_to_user(...)
        switch_to_alias(api, user_id, alias)
        return

    # ---------- (B) 呼叫對應的 handler ----------
    module_path = ACTION_DISPATCH.get(action)
    if module_path:
        mod = import_module(module_path)

        # 支援多種命名：handle(api,event) / handle(event) / handle_XYZ(api,event)
        if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
            return mod.handle(api, event)
        if hasattr(mod, "handle"):
            return mod.handle(event)
        if hasattr(mod, "handle_current_message"):
            return mod.handle_current_message(api, event)
        if hasattr(mod, "handle_forecast_postback"):
            return mod.handle_forecast_postback(api, event)

        raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

    # ---------- (C) 若沒有對應 action ----------
    logger.warning(f"未知的 postback action: {action}")
    send_line_reply_message(api, event.reply_token,
        [TextMessage(text="抱歉，我不太懂您的選擇，請再試一次。")])             # handle(event) (舊版)