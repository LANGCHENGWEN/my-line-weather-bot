# handlers/postback_router.py
# 中央控制台，接收所有來自使用者點擊按鈕的 PostbackEvent
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import PostbackEvent

from urllib.parse import parse_qs
from utils.api_helper import get_messaging_api
from utils.firestore_manager import set_user_state, get_default_city
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
ACTION_DISPATCH_HANDLERS = {
    # 專門處理設定狀態的 action
    "change_city"         : ("handlers.postback_router", "handle_change_city"),
    "forecast_other_city" : ("handlers.postback_router", "handle_forecast_other_city"),
    "outfit_other_city"   : ("handlers.postback_router", "handle_outfit_other_city"),
    "change_default_city" : ("handlers.postback_router", "handle_change_default_city"),
    "return_to_main_menu" : ("handlers.postback_router", "handle_return_to_main_menu"),

    # 通用模組處理
    "forecast_days"             : ("weather_forecast.postback_handler", "handle_forecast_postback"), # 未來預報的天數選單
    "outfit_advisor"            : ("outfit_suggestion.outfit_handler", "handle_outfit_advisor"), # 穿搭建議子選單
    "outfit_query"              : ("outfit_suggestion.outfit_handler", "handle_outfit_query"), # 穿搭建議類型的flex message選單
    "weekend_weather"           : ("weekend_weather.weekend_handler", "handle_weekend_weather_postback"), # 週末天氣子選單
    "solar_term_info"           : ("solar_terms.solar_terms_handler", "handle_solar_term_query"), # 節氣小知識子選單
    "daily_reminder_push"       : ("settings.settings_handler", "handle_settings_postback"), # 每日提醒推播
    "typhoon_notification_push" : ("settings.settings_handler", "handle_settings_postback"), # 颱風通知推播
    "weekend_weather_push"      : ("settings.settings_handler", "handle_settings_postback"), # 週末天氣推播
    "solar_terms_push"          : ("settings.settings_handler", "handle_settings_postback"), # 節氣小知識推播
    "set_status"                : ("settings.settings_handler", "handle_settings_postback")
}

def _set_state_and_reply(api, event, action: str, state_name: str, reply_text: str):
    """
    通用輔助函式：設定用戶狀態、發送回覆並記錄日誌。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    set_user_state(user_id, state_name)
    send_line_reply_message(api, reply_token, [TextMessage(text=reply_text)])
    
    logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇 {action}，狀態設為 {state_name}。")
    return True

# 🌟 簡化後的 action 處理函式 🌟
def handle_change_city(api, event):
    return _set_state_and_reply(
        api, event,
        action="查詢即時天氣其他縣市",
        state_name="awaiting_city_input",
        reply_text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市"
    )

def handle_forecast_other_city(api, event):
    return _set_state_and_reply(
        api, event,
        action="查詢未來預報其他縣市",
        state_name="awaiting_forecast_city_input",
        reply_text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市"
    )

def handle_outfit_other_city(api, event):
    return _set_state_and_reply(
        api, event,
        action="查詢穿搭建議其他縣市",
        state_name="awaiting_outfit_city_input",
        reply_text="請輸入您想查詢的縣市名稱，例如：台中市 或 台北市"
    )

def handle_change_default_city(api, event):
    user_id = event.source.user_id

    # 1. 取得用戶目前的預設城市
    current_default_city = get_default_city(user_id)
    if not current_default_city:
        current_default_city = "未設定預設城市" # 如果找不到預設城市，顯示「未設定」

    # 2. 組合新的回覆文字
    combined_text = (
        f"您目前的預設城市是：{current_default_city}\n\n"
        "請輸入您想設定的預設城市名稱，例如：台中市 或 台北市"
    )

    return _set_state_and_reply(
        api, event,
        action="切換預設城市",
        state_name="awaiting_default_city_input",
        reply_text=combined_text
    )

def handle_return_to_main_menu(api, event):
    user_id = event.source.user_id
    logger.info(f"[PostbackRouter] 用戶 {user_id} 點擊「回上一頁」Postback，切換回主選單。")
    return switch_to_alias(api, user_id, MAIN_MENU_ALIAS)

# -------------------- 3) 通用函式：安全地調用處理器 --------------------
def _call_handler(module_path: str, handler_name: str, api, event) -> bool:
    """
    通用函式：安全地從指定模組中調用指定的處理函式。
    """
    try:
        mod = import_module(module_path)
        handler_func = getattr(mod, handler_name)
        
        # 檢查函式需要的參數數量，以確保呼叫正確
        arg_count = handler_func.__code__.co_argcount
        if arg_count == 2:
            return handler_func(api, event)
        else:
            logger.error(f"[PostbackRouter] 處理函式 '{handler_name}' 參數數量不正確 ({arg_count})。")
            return False
            
    except (ImportError, AttributeError) as e:
        logger.error(f"[PostbackRouter] 無法調用處理函式 {handler_name}。模組或函式不存在: {e}")
        send_line_reply_message(api, event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部配置錯誤。")])
        return False
    except Exception as e:
        logger.exception(f"[PostbackRouter] 調用處理函式 {handler_name} 時發生未預期錯誤: {e}")
        send_line_reply_message(api, event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部錯誤。")])
        return False

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

    # 1. 處理 Rich Menu 切換
    alias = ACTION_TO_ALIAS.get(action)
    if alias:
        # switch_to_alias 需在 menu_switcher 裡面封裝 link_rich_menu_id_to_user(...)
        switch_to_alias(api, user_id, alias)
        logger.info(f"[PostbackRouter] 用戶 {user_id} 切換 Rich Menu 別名至 {alias}。")
        return True # 必須要 return True
    
    # 2. 處理需要導向特定模組並呼叫特定函式的 action
    # 🌟 用字典取代冗長的 if/elif 區塊 🌟
    handler_info = ACTION_DISPATCH_HANDLERS.get(action)
    if handler_info:
        module_path, handler_name = handler_info
        logger.debug(f"[PostbackRouter] 導向 {module_path}.{handler_name} 處理 action '{action}'。")
        return _call_handler(module_path, handler_name, api, event)

    # 3. 若沒有對應 action 也沒有導向模組
    logger.warning(f"[PostbackRouter] 未知的 postback action: {action}")
    send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，我不太懂您的選擇，請再試一次。")])
    return True # 已回覆，所以返回 True