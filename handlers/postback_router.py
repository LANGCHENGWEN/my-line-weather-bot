# handlers/postback_router.py
# 中央控制台，接收所有來自使用者點擊按鈕的 PostbackEvent
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import PostbackEvent

from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.user_data_manager import set_user_state, get_default_city
from utils.line_common_messaging import send_line_reply_message

from menu_handlers.menu_switcher import switch_to_alias
# 引入主選單別名，用於回上一頁
from rich_menu_manager.rich_menu_configs import MAIN_MENU_ALIAS
from weather_forecast.postback_handler import handle_forecast_postback
from weather_forecast.forecast_handler import reply_forecast_weather_of_city

'''
from weather_current import current_handler
from weather_typhoon import typhoon_handler
from life_style import reminder_handler
from menu_handlers import settings_menu_handler
'''

logger = logging.getLogger(__name__)

# -------------------- 1) Rich‑menu 別名對照 --------------------
# alias 需與 rich_menu_configs.py 及 JSON 別名一致 (Rich‑menu 母選單)
# 定義特定使用者行為（按鈕行動）如何導致切換到這些已命名的 Rich Menu
ACTION_TO_ALIAS = {
    "weather_query"       : "weather_query_alias",
    "typhoon_area"        : "typhoon_zone_alias",
    "lifestyle_reminders" : "life_reminder_alias",
    "settings"            : "settings_alias",
}

# 所有 action 與「子 handler 模組路徑」的對照 (Rich‑menu 子選單)
ACTION_DISPATCH = {
    "forecast_days"       : "weather_forecast.postback_handler", # 未來預報的天數選單
    "outfit_advisor"      : "outfit_suggestion.outfit_handler",     # 穿搭建議子選單
    "outfit_query"        : "outfit_suggestion.outfit_handler",     # 穿搭建議類型的flex message選單
    "weekend_weather"     : "weekend_weather.weekend_handler",
    "solar_term_info"     : "life_reminders.",
    "settings"            : "menu_handlers.settings_menu_handler"
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
    logger.debug(f"[PostbackRouter] 原始 Postback data: {event.postback.data}") # 記錄完整 data 方便除錯

    # --- 優先級邏輯 ---
    # 1. 直接處理需要設定狀態或特殊回覆的 action (通常這些 action 會導致後續的文字輸入)
    if action == "change_city":
        set_user_state(user_id, "awaiting_city_input")
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇查詢即時天氣其他縣市，狀態設為 awaiting_city_input。")
        return True # 已處理
    
    elif action == "forecast_other_city":
        set_user_state(user_id, "awaiting_forecast_city_input")
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇查詢未來預報其他縣市，狀態設為 awaiting_forecast_city_input。")
        return True # 已處理

    elif action == "outfit_other_city":
        set_user_state(user_id, "awaiting_outfit_city_input")
        send_line_reply_message(api, reply_token, [TextMessage(text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市")])
        logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇查詢穿搭建議其他縣市，狀態設為 awaiting_outfit_city_input。")
        return True # 已處理
    
    # 處理返回主選單的 postback action (通常是最優先處理的選單切換)
    elif action == "return_to_main_menu":
        logger.info(f"[PostbackRouter] 用戶 {user_id} 點擊「回上一頁」Postback，切換回主選單。")
        # 直接呼叫 switch_to_alias，它會執行 Rich Menu 切換且不發送回覆訊息
        # 不需要 send_line_reply_message
        return switch_to_alias(api, user_id, MAIN_MENU_ALIAS) 
        # switch_to_alias 會返回 True/False 表示是否成功，這裡直接返回它的結果

    # 2. 處理需要切換 Rich Menu 的 action (如果你的 Rich Menu 觸發行為只在 ACTION_TO_ALIAS 中)
    alias = ACTION_TO_ALIAS.get(action)
    if alias:
        # switch_to_alias 需在 menu_switcher 裡面封裝 link_rich_menu_id_to_user(...)
        switch_to_alias(api, user_id, alias)
        logger.info(f"[PostbackRouter] 用戶 {user_id} 切換 Rich Menu 別名至 {alias}。")
        return True # 必須要 return True
    
    # 3. 處理需要導向特定模組並呼叫特定函式的 action
    module_path = ACTION_DISPATCH.get(action)
    if module_path:
        try:
            mod = import_module(module_path)
        
            # 🚀 優化點 2: 處理 forecast_days
            # 因為這個 action 是特定且需要解析參數的，所以單獨處理
            if action == "forecast_days": # 處理未來預報的天數選單
                # 直接呼叫專門處理 forecast_days 的函數
                # 這個函數 (handle_postback_forecast_query) 需要從 event 中自行解析 days 和 city
                logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_forecast_postback 處理 forecast_days。")
                return mod.handle_forecast_postback(api, event)

            # 處理穿搭建議子選單
            elif action == "outfit_advisor" and hasattr(mod, "handle_outfit_advisor"):
                logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_outfit_advisor 處理 outfit_advisor。")
                return mod.handle_outfit_advisor(api, event)
            
            # 處理通用的穿搭建議類型 Postback
            elif action == "outfit_query" and hasattr(mod, "handle_outfit_query"):
                logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_outfit_query 處理 outfit_query。")
                return mod.handle_outfit_query(api, event)
            
            elif action == "weekend_weather" and hasattr(mod, "handle_weekend_weather_postback"):
                # 假設 weekend_handler.py 裡面有一個叫做 handle_weekend_weather_postback 的函數
                logger.debug(f"[PostbackRouter] 導向 {module_path}.handle_weekend_weather_postback 處理 weekend_weather。")
                return mod.handle_weekend_weather_postback(api, event)
        
            # Fallback 處理：通用 handle 函數或其他特定命名函數
            elif hasattr(mod, "handle"):
                if mod.handle.__code__.co_argcount == 2: # handle(api, event)
                    logger.debug(f"[PostbackRouter] 導向 {module_path}.handle(api, event)")
                    return mod.handle(api, event)
                elif mod.handle.__code__.co_argcount == 1: # handle(event)
                    logger.debug(f"[PostbackRouter] 導向 {module_path}.handle(event)")
                    return mod.handle(event)
            
            # 如果找到模組但沒有匹配的處理函數
            logger.error(f"[PostbackRouter] {module_path} 沒有可用的處理函式來處理 action '{action}'。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部配置錯誤。")])
            return True # 配置錯誤，回覆用戶後停止
    
        except Exception as e:
                logger.exception(f"[PostbackRouter] 處理 action '{action}' 時發生錯誤: {e}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部錯誤。")])
                return True # 處理錯誤，回覆用戶後停止

    # 4. 若沒有對應 action 也沒有導向模組
    logger.warning(f"[PostbackRouter] 未知的 postback action: {action}")
    send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，我不太懂您的選擇，請再試一次。")])
    return True # 已回覆，所以返回 True