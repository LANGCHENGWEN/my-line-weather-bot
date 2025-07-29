# handlers/text_router.py
# 主要文字訊息分發器，負責接收所有來自使用者的文字訊息
# from utils.api_helper import get_api
import logging
from importlib import import_module
from linebot.v3.messaging.models import TextMessage

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message # 引入共用訊息發送函式
from utils.user_data_manager import get_user_state, clear_user_state
# from menu_handlers.menu_switcher import handle_menu_switching as switch

logger = logging.getLogger(__name__)

# 狀態 → handler
DISPATCH_STATE = {
    "awaiting_default_city_input"  : "handlers.city_input_handler", # 等待輸入預設城市
    "awaiting_city_input"          : "handlers.city_input_handler", # 等待輸入查詢即時天氣其他縣市
    "awaiting_forecast_city_input" : "handlers.city_input_handler", # 等待輸入查詢未來預報其他縣市
    "awaiting_outfit_city_input"   : "handlers.city_input_handler" # 等待輸入查詢穿搭建議其他縣市
    # "awaiting_township_input": "weather_forecast.forecast_handler", # 等待輸入鄉鎮市區
    # "awaiting_full_location":  "weather_forecast.forecast_handler"  # 等待輸入縣市+鄉鎮市區
}

# 關鍵字 → handler
DISPATCH_KEYWORD = {
    "即時天氣":"weather_current.current_handler",
    "未來預報":"weather_forecast.forecast_handler",
    "颱風現況":"typhoon.typhoon_handler",
    "地區影響預警":"typhoon.area_hazard_handler"
    # …
}

POSTBACK_RELATED_TEXTS_TO_IGNORE = [
    "天氣查詢", "颱風專區", "生活提醒", "設定", "回上一頁",
    "颱風路徑圖", "穿搭建議", "週末天氣", "節氣小知識",
    "每日提醒推播", "颱風通知推播", "週末天氣推播", "節氣小知識推播",
    "切換預設城市"    # 如果是 Postback 按鈕的顯示文字
    # ... 請根據你的所有 Rich Menu Postback 按鈕的 'label' (顯示文字) 來補充這個列表
]

def _dispatch_to_module(module_path: str, event, user_state_info: dict):
    """
    根據模組路徑和當前狀態，調用對應模組中的處理函式。
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
    # 統一調用約定好的狀態處理函式名稱 (這段會保持在 text_router 內部)
    handler_func_name = None
    if state == "awaiting_default_city_input":
        handler_func_name = "handle_awaiting_default_city_input"
    elif state == "awaiting_city_input":
        handler_func_name = "handle_awaiting_city_input"
    elif state == "awaiting_forecast_city_input":
        handler_func_name = "handle_awaiting_forecast_city_input"
    elif state == "awaiting_outfit_city_input":
        handler_func_name = "handle_awaiting_outfit_city_input"

    if handler_func_name and hasattr(mod, handler_func_name):
        logger.debug(f"導向至 {module_path}.{handler_func_name} for state: {state}")
        # 假設所有狀態處理函式都接收 (api, event)
        return getattr(mod, handler_func_name)(api, event)
    
    # 如果不是特定狀態的處理，則嘗試調用通用函式
    if hasattr(mod, "handle_current_message"):
        logger.debug(f"導向至 {module_path}.handle_current_message")
        return mod.handle_current_message(api, event)
    elif hasattr(mod, "handle_forecast_message"):
        logger.debug(f"導向至 {module_path}.handle_forecast_message")
        return mod.handle_forecast_message(api, event)
    elif hasattr(mod, "handle_typhoon_message"):
        logger.debug(f"導向至 {module_path}.handle_typhoon_message")
        return mod.handle_typhoon_message(api, event)
    elif hasattr(mod, "handle_area_hazard_message"):
        logger.debug(f"導向至 {module_path}.handle_area_hazard_message")
        return mod.handle_area_hazard_message(api, event)
    
    # Fallback 到通用的 handle 函式 (優先 api, event，其次 event)
    elif hasattr(mod, "handle"):
        if mod.handle.__code__.co_argcount == 2: # handle(api, event)
            logger.debug(f"導向至 {module_path}.handle(api, event)")
            return mod.handle(api, event)
        elif mod.handle.__code__.co_argcount == 1: # handle(event)
            logger.debug(f"導向至 {module_path}.handle(event)")
            return mod.handle(event)
    
    logger.error(f"{module_path} 沒有可用的處理函式來處理當前事件或狀態。")
    # 如果沒有匹配到任何處理函式，或者調用的函式沒有返回，這裡可以返回 False 讓上層繼續處理
    return False

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

    logger.debug(f"路由器狀態 = {user_state_info} (user_id={user_id})")
    logger.debug(f"用戶輸入訊息: {message_text}")

    # --- 路由優先級邏輯 ---
    # 1. 檢查是否為 Postback 副作用文字，如果是則直接忽略 (最高優先級)
    if message_text in POSTBACK_RELATED_TEXTS_TO_IGNORE:
        logger.info(f"[TextRouter] 偵測到 Postback 相關文字 '{message_text}'，由 TextRouter 忽略以避免重複回覆。")
        return # 直接返回，不進行後續處理，因為 Postback 事件已經被 postback_router 處理
    
    # 2. 處理用戶處於特定「狀態」下的輸入
    # 如果狀態處理器處理成功 (返回 True)，則立即停止處理
    if state and state != "idle" and state in DISPATCH_STATE:
        module_path = DISPATCH_STATE[state]
        logger.info(f"[TextRouter] 依照用戶狀態 '{state}' 導向處理模組: {module_path}。")
        try:
            handled = _dispatch_to_module(module_path, event, user_state_info)
            if handled: 
                logger.info(f"[TextRouter] 狀態處理器 '{module_path}' 已成功處理訊息並回覆。")
                return # 成功處理，立即結束
            else:
                # 如果狀態處理器返回 False (表示輸入無效但已提示用戶重試)，Text Router 仍應停止
                # 這是為了避免 default 處理器發送重複的「不明白」訊息
                logger.info(f"[TextRouter] 狀態處理器 '{module_path}' 未完全處理訊息 (可能提示重試)，Text Router 停止處理。")
                return # 停止，避免落入 default 處理器
        except AttributeError as e:
            logger.error(f"[TextRouter] 錯誤: {e}. 請檢查 {module_path} 中是否有對應狀態的處理函式。")
            send_line_reply_message(get_messaging_api(), event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生內部配置錯誤。")])
            clear_user_state(user_id) # 出錯時清除狀態，避免卡住
            return # 發生配置錯誤，回覆用戶後停止
        except Exception as e:
            logger.exception(f"[TextRouter] 處理狀態 '{state}' 時發生未預期錯誤。")
            send_line_reply_message(get_messaging_api(), event.reply_token, [TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍候再試。")])
            clear_user_state(user_id) # 出錯時清除狀態，避免卡住
            return # 發生運行錯誤，回覆用戶後停止
        
    # 3. 處理精確匹配的「全局關鍵字」
    # 如果關鍵字處理器處理成功 (返回 True)，則立即停止處理
    if message_text in DISPATCH_KEYWORD:
        module_path = DISPATCH_KEYWORD[message_text]
        logger.info(f"[TextRouter] 偵測到精確匹配關鍵字 '{message_text}'，導向至 {module_path}。")
        try:
            handled = _dispatch_to_module(module_path, event, user_state_info)
            if handled:
                logger.info(f"[TextRouter] 關鍵字處理器 '{module_path}' 已成功處理訊息並回覆。")
                return # 成功處理，立即結束
            else:
                # 如果關鍵字處理器返回 False (例如，特定關鍵字但查詢失敗且已回覆錯誤)
                logger.info(f"[TextRouter] 關鍵字處理器 '{module_path}' 未完全處理訊息。")
                return # 停止，避免落入 default 處理器
        except AttributeError as e:
            logger.error(f"[TextRouter] 錯誤: {e}. 請檢查 {module_path} 中是否有對應關鍵字的處理函式。")
            send_line_reply_message(get_messaging_api(), event.reply_token, [TextMessage(text="抱歉，處理您的指令時發生內部配置錯誤。")])
            return # 發生配置錯誤，回覆用戶後停止
        except Exception as e:
            logger.exception(f"[TextRouter] 處理關鍵字 '{message_text}' 時發生未預期錯誤。")
            send_line_reply_message(get_messaging_api(), event.reply_token, [TextMessage(text="抱歉，處理您的指令時發生錯誤，請稍候再試。")])
            return # 發生運行錯誤，回覆用戶後停止

    logger.info(f"[TextRouter] 未匹配任何特定規則，導向至最終處理模組: handlers.default。")
    try:
        # handlers.default 模組的 handle 函式預期接收 (api, event)
        _dispatch_to_module("handlers.default", event, user_state_info)
    except Exception as e:
        logger.exception(f"[TextRouter] 處理 default 模組時發生錯誤: {e}")

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