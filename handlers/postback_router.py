# handlers/postback_router.py
"""
中央控制台，接收所有來自用戶點擊按鈕的 Postback 事件。
這個檔案是 LINE Bot 處理 Postback 事件的核心路由器。
它的主要職責是解析用戶點擊 Rich Menu 或 Flex Message 按鈕後傳來的 `postback.data`，並根據其中的 `action` 參數，執行對應的邏輯。
這些邏輯包含：
1. 切換 Rich Menu (圖文選單)。
2. 設定特定的用戶狀態，以引導後續的文字輸入。
3. 導向到不同的模組與函式，以處理特定的業務功能。
"""
import logging
from urllib.parse import parse_qs # 用於解析 Postback data
from importlib import import_module
from linebot.v3.messaging.models import TextMessage

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import set_user_state, get_default_city

from menu_handlers.menu_switcher import switch_to_alias

# 導入主選單別名，用於回首頁
from rich_menu_manager.rich_menu_configs import MAIN_MENU_ALIAS

logger = logging.getLogger(__name__)

# --- Rich Menu 別名對照 ---
"""
定義從 Postback 的 `action` 到 Rich Menu 別名 (alias) 的映射關係。
alias 需與 rich_menu_manager/rich_menu_configs.py 的別名一致 (Rich Menu 母選單)。
當用戶點擊 Rich Menu 上的某個母選單功能按鈕時，Rich Menu 介面也能跟著切換到對應的子選單。
"""
ACTION_TO_ALIAS = {
    "weather_query"       : "weather_query_alias", # 天氣查詢母選單
    "typhoon_area"        : "typhoon_zone_alias",  # 颱風專區母選單
    "lifestyle_reminders" : "life_reminder_alias", # 生活提醒母選單
    "settings"            : "settings_alias"       # 設定母選單
}

# --- 所有 action 與「子 handler 模組路徑」的對照 (Rich Menu 子選單) ---
"""
定義所有 Postback 的 `action` 到其對應處理函式的映射。
透過一個中央字典來映射 `action` 和處理函式的「模組路徑」與「函式名稱」，可以避免在單一函式中寫冗長的 `if/elif` 判斷式。
當新增一個功能時，只需要在字典中加入一個新的映射關係即可，而不需要修改核心的路由器邏輯。
"""
ACTION_DISPATCH_HANDLERS = {
    # 專門處理設定狀態的 action
    "change_city"         : ("handlers.postback_router", "handle_change_city"),         # 查詢即時天氣其他縣市時，等待用戶輸入
    "forecast_other_city" : ("handlers.postback_router", "handle_forecast_other_city"), # 查詢未來預報其他縣市時，等待用戶輸入
    "outfit_other_city"   : ("handlers.postback_router", "handle_outfit_other_city"),   # 查詢穿搭建議其他縣市時，等待用戶輸入
    "change_default_city" : ("handlers.postback_router", "handle_change_default_city"), # 切換預設城市時，等待用戶輸入
    "set_status"          : ("settings.settings_handler", "handle_settings_postback"),  # 推播狀態設定

    # 通用模組處理
    "return_to_main_menu"       : ("handlers.postback_router", "handle_return_to_main_menu"),             # 點擊「回首頁」Postback，切換回母選單
    "forecast_days"             : ("weather_forecast.postback_handler", "handle_forecast_postback"),      # 未來預報的天數選單
    "outfit_advisor"            : ("outfit_suggestion.outfit_handler", "handle_outfit_advisor"),          # 穿搭建議子選單
    "outfit_query"              : ("outfit_suggestion.outfit_handler", "handle_outfit_query"),            # 穿搭建議時段的 flex message 選單
    "weekend_weather"           : ("weekend_weather.weekend_handler", "handle_weekend_weather_postback"), # 週末天氣子選單
    "solar_term_info"           : ("solar_terms.solar_terms_handler", "handle_solar_term_query"),         # 節氣小知識子選單
    "daily_reminder_push"       : ("settings.settings_handler", "handle_settings_postback"),              # 今日天氣推播
    "typhoon_notification_push" : ("settings.settings_handler", "handle_settings_postback"),              # 颱風通知推播
    "weekend_weather_push"      : ("settings.settings_handler", "handle_settings_postback"),              # 週末天氣推播
    "solar_terms_push"          : ("settings.settings_handler", "handle_settings_postback")               # 節氣小知識推播
}

# --- 通用輔助函式：設定用戶狀態、發送回覆並記錄日誌 ---
def _set_state_and_reply(api, event, action: str, state_name: str, reply_text: str):
    """
    這是為了避免在多個函式中重複相同的「設定狀態 -> 回覆訊息 -> 記錄日誌」這三個步驟。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    set_user_state(user_id, state_name)
    send_line_reply_message(api, reply_token, [TextMessage(text=reply_text)])
    
    logger.info(f"[PostbackRouter] 用戶 {user_id} 選擇 {action}，狀態設為 {state_name}。")
    return True

"""
以下的 4 個函式都是為了回應用戶點擊「查詢其他縣市」或「切換預設城市」的按鈕。
這些按鈕的主要目的不是立即回覆資訊，而是將用戶帶入一個特定的狀態，讓 bot 準備好接收用戶接下來的文字輸入（即縣市名稱）。
透過呼叫通用的 `_set_state_and_reply` 輔助函式，可以精簡程式碼，並確保設定狀態和發送提示訊息的邏輯一致。
"""
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
        current_default_city = "未設定預設城市" # 如果找不到預設城市，顯示「未設定預設城市」

    # 2. 顯示用戶目前的預設城市
    combined_text = (
        f"您目前的預設城市是：{current_default_city}\n\n"
        "請輸入您想設定的預設城市名稱，例如：台中市 或 台北市"
    )

    # 3. 設定狀態並等待用戶輸入城市名稱
    return _set_state_and_reply(
        api, event,
        action="切換預設城市",
        state_name="awaiting_default_city_input",
        reply_text=combined_text
    )

# --- 處理「回首頁」的 Postback 事件 ---
def handle_return_to_main_menu(api, event):
    """
    此函式的目的只有一個：切換回母選單。
    """
    user_id = event.source.user_id
    logger.info(f"[PostbackRouter] 用戶 {user_id} 點擊「回首頁」Postback，切換回母選單。")
    return switch_to_alias(api, user_id, MAIN_MENU_ALIAS)

# --- 通用函式：安全的從指定模組中調用指定的處理函式 ---
def _call_handler(module_path: str, handler_name: str, api, event) -> bool:
    """
    用 `importlib` 在程式執行時動態載入模組，並使用 `getattr` 安全的取得對應的處理函式。
    這種動態調用機制可以避免在檔案開頭靜態的 import 所有處理函式，減少不必要的程式碼載入，並讓中央控制台的程式碼更加簡潔。
    `try...except` 區塊可以捕捉載入或呼叫函式時可能發生的錯誤，確保程式不會因為配置問題而崩潰。
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

# --- Postback 事件的主要處理入口函式 ---
# 根據 Postback 的 `action` 參數來決定接下來的處理步驟
# 優先處理 Rich Menu 的切換，然後再調用對應的業務邏輯處理函式
def handle(event):
    """
    收到 Postback 事件之後：
       1. 解析 action
       2. 先切換 Rich Menu (如果對應得到 alias)
       3. 再看有沒有對應 handler，有就呼叫
       4. 都沒有就回覆「不明白」
    """
    api = get_messaging_api()
    data = parse_qs(event.postback.data)
    action = data.get("action", [""])[0]
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.debug(f"[PostbackRouter] 收到 Postback 事件. Action: {action}, 用戶: {user_id}")

    # 1. 處理 Rich Menu 切換
    """
    這是路由器的第一步。
    檢查 Postback 的 `action` 是否與 `ACTION_TO_ALIAS` 字典中的 Rich Menu 別名有對應關係。
    立即處理 Rich Menu 切換，可以確保用戶介面（Rich Menu）能夠即時更新，提供流暢的互動體驗。
    處理完畢後，會直接回傳 `True` 來終止後續的處理，因為這個 Postback 的主要目的已經達成。
    """
    alias = ACTION_TO_ALIAS.get(action)
    if alias:
        # switch_to_alias 需在 menu_handlers/menu_switcher.py 裡面封裝 link_rich_menu_id_to_user(...)
        switch_to_alias(api, user_id, alias)
        logger.info(f"[PostbackRouter] 用戶 {user_id} 切換 Rich Menu 別名至 {alias}。")
        return True
    
    # 2. 處理需要導向特定模組並呼叫特定函式的 action
    """
    這是路由器的核心邏輯。
    檢查 `action` 是否在 `ACTION_DISPATCH_HANDLERS` 字典中有對應的處理函式。
    當偵測到對應的 `action` 時，會呼叫前面定義的 `_call_handler` 輔助函式，該函式會動態載入和執行真正的業務邏輯。
    用字典取代冗長的 if/elif 區塊，這種設計模式將路由決策與實際業務邏輯分離開來，使得新增或修改功能變得非常簡單，只需要更新這個字典即可。
    """
    handler_info = ACTION_DISPATCH_HANDLERS.get(action)
    if handler_info:
        module_path, handler_name = handler_info
        logger.debug(f"[PostbackRouter] 導向 {module_path}.{handler_name} 處理 action '{action}'。")
        return _call_handler(module_path, handler_name, api, event)

    # 3. 若沒有對應 action ，也沒有導向模組
    """
    這是路由器的最後一道防線。
    如果一個 Postback 的 `action` 既沒有對應的 Rich Menu 別名，也沒有對應的處理函式，為了避免 bot 保持沉默或出錯，會發送一個通用的錯誤回覆給用戶，並記錄警告日誌。
    回傳 `True` 確保事件被標記為已處理，防止其他地方嘗試再次處理這個未知的 Postback。
    """
    logger.warning(f"[PostbackRouter] 未知的 postback action: {action}")
    send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，我不太懂您的選擇，請再試一次。")])
    return True