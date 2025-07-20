# handlers/postback_router.py
# 中央控制台，接收所有來自使用者點擊按鈕的 PostbackEvent
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.user_data_manager import set_user_state, get_user_state
from utils.line_common_messaging import send_line_reply_message

from menu_handlers.menu_switcher import switch_to_alias
# 引入主選單別名，用於回上一頁
from rich_menu_manager.rich_menu_configs import MAIN_MENU_ALIAS
from weather_forecast.postback_handler import handle_forecast_postback

'''
from weather_current import current_handler
from weather_typhoon import typhoon_handler
from life_style import reminder_handler
from menu_handlers import settings_menu_handler
'''

logger = logging.getLogger(__name__)

# -------------------- 1) Rich‑menu 別名對照 --------------------
# alias 需與 rich_menu_configs.py 及 JSON 別名一致
# 定義特定使用者行為（按鈕行動）如何導致切換到這些已命名的 Rich Menu
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
    "forecast_days"      : "weather_forecast.postback_handler",
    "typhoon_area"       : "weather_typhoon.typhoon_handler",
    "lifestyle_reminders": "life_style.reminder_handler",
    "settings"           : "menu_handlers.settings_menu_handler"
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
    reply_token = event.reply_token

    logger.debug(f"[PostbackRouter] 收到 Postback 事件. Action: {action}, 用戶: {user_id}")

    # 🚀 優化點 1: 直接處理 change_city 和 forecast_other_city 的狀態設定
    if action == "change_city":
        set_user_state(user_id, "awaiting_city_input")
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇查詢即時天氣其他縣市，狀態設為 awaiting_city_input。")
        return True # 已處理
    
    # 判斷 forecast_other_city
    if action == "forecast_other_city":
        set_user_state(user_id, "awaiting_forecast_city_input")
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇查詢未來預報其他縣市，狀態設為 awaiting_forecast_city_input。")
        return True # 已處理
    
    # 🚀 優化點 2: 處理 forecast_days
    # 因為這個 action 是特定且需要解析參數的，所以單獨處理
    if action == "forecast_days": # 處理未來預報的天數選單
        # 直接呼叫專門處理 forecast_days 的函數
        # 這個函數 (handle_postback_forecast_query) 需要從 event 中自行解析 days 和 city
        logger.debug(f"[PostbackRouter] 導向 handle_postback_forecast_query 處理 forecast_days。")
        return handle_forecast_postback(api, event) # 這會回傳 True/False
    
    # --- 新增: 處理返回主選單的 postback action ---
    if action == "return_to_main_menu":
        logger.info(f"[PostbackRouter] 用戶 {user_id} 點擊「回上一頁」Postback，切換回主選單。")
        # 直接呼叫 switch_to_alias，它會執行 Rich Menu 切換且不發送回覆訊息
        # 不需要 send_line_reply_message
        return switch_to_alias(api, user_id, MAIN_MENU_ALIAS) 
        # switch_to_alias 會返回 True/False 表示是否成功，這裡直接返回它的結果

    # ---------- (A) 切換 Rich‑menu ----------
    alias = ACTION_TO_ALIAS.get(action)
    if alias:
        # switch_to_alias 需在 menu_switcher 裡面封裝 link_rich_menu_id_to_user(...)
        switch_to_alias(api, user_id, alias)
        logger.info(f"[PostbackRouter] 用戶 {user_id} 切換 Rich Menu 別名至 {alias}。")
        return True # 已處理

    # ---------- (B) 呼叫對應的 handler ----------
    module_path = ACTION_DISPATCH.get(action)
    if module_path:
        mod = import_module(module_path)

        # 支援多種命名：handle(api,event) / handle(event) / handle_XYZ(api,event)
        if hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 2:
            logger.debug(f"[PostbackRouter] 導向 {module_path}.handle(api, event)")
            return mod.handle(api, event)
        elif hasattr(mod, "handle") and mod.handle.__code__.co_argcount == 1:
            logger.debug(f"[PostbackRouter] 導向 {module_path}.handle(event)")
            return mod.handle(event)
        elif hasattr(mod, "handle_current_message"):
            logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_current_message(api, event)")
            return mod.handle_current_message(api, event)
        elif hasattr(mod, "handle_forecast_postback"):
            logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_forecast_postback(api, event)")
            return mod.handle_forecast_postback(api, event)
        elif hasattr(mod, "handle_postback_forecast_query"): # 🚀 確保這裡能導向你新增的函數
            logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_postback_forecast_query(api, event)")
            return mod.handle_postback_forecast_query(api, event)

        # 如果找到模組但沒有匹配的處理函數
        logger.error(f"[PostbackRouter] {module_path} 沒有可用的 handle 函式 (或簽名不符)。")
        raise AttributeError(f"{module_path} 沒有可用的 handle 函式")

    # ---------- (C) 若沒有對應 action ----------
    logger.warning(f"[PostbackRouter] 未知的 postback action: {action}")
    send_line_reply_message(api, reply_token,
        [TextMessage(text="抱歉，我不太懂您的選擇，請再試一次。")])
    return True # 已回覆，所以返回 True