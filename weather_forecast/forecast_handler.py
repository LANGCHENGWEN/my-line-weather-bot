# weather_forecast/forecast_handler.py
"""
處理與天氣預報相關的用戶輸入和回覆邏輯。
處理兩種主要情境：
1. 當用戶輸入「未來預報」等關鍵字時，回覆一個 Flex Message 選單，讓用戶選擇預報天數，並將用戶狀態設定為等待選擇。
2. 當其他模組（例如 `city_input_handler`）處理完用戶輸入的縣市名稱後，這個模組會被調用，根據用戶輸入的城市，再次回覆一個天數選擇選單，但這次的查詢目標城市會是用戶指定的城市。
"""
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import MessageEvent

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import set_user_state, get_default_city # 導入用戶數據管理器

from .forecast_options_flex import create_forecast_options_flex_message

logger = logging.getLogger(__name__)

# --- 與天氣預報相關的文字訊息 ---
def handle_forecast_message(messaging_api, event: MessageEvent) -> bool:
    """
    檢查用戶輸入是否為「未來預報」；如果是，則觸發天氣預報的對話流程。
    根據用戶是否已設定預設城市來決定初始查詢的城市，並回覆一個天數選擇的 Flex Message。
    如果訊息被此 handler 處理，則返回 True，否則返回 False，讓其他 handler 繼續處理。
    """
    user_id = event.source.user_id
    message_text = event.message.text
    reply_token = event.reply_token

    # 處理啟動天氣查詢的關鍵字
    if message_text == "未來預報":
        """
        先嘗試從資料庫取得用戶設定的預設城市；如果沒有設定，則使用「臺中市」作為預設值。
        `normalize_city_name` 函式確保城市名稱格式統一，例如「臺中」和「台中」都會被處理成一致的名稱。
        """
        # 獲取用戶的預設城市，如果沒有則使用 "臺中市"
        raw_default_city = get_default_city(user_id)

        # 實際查詢用的城市名稱，進行正規化
        target_query_city = normalize_city_name(raw_default_city or "臺中市")

        # Flex Message 顯示用的城市名稱
        default_display_city = normalize_city_name(raw_default_city) if raw_default_city else "未設定"
        
        # 建立並發送 Flex Message
        flex_message = create_forecast_options_flex_message(
            default_county=default_display_city, # 用於顯示的預設城市
            target_query_city=target_query_city  # 用於實際查詢的目標城市
        )
        send_line_reply_message(messaging_api, reply_token, [flex_message])
        logger.info(f"用戶 {user_id} 請求未來預報，已回覆天數選單。")

        # 更新用戶狀態
        """
        在回覆選單後，程式會將用戶的狀態設定為 `awaiting_forecast_selection`。
        為了追蹤對話流程，以便在用戶點擊選單上的按鈕時，主程式能夠知道這是一個天氣預報的選擇動作，並根據附帶的 `data`（包含目標城市）來進行下一步的查詢。
        """
        set_user_state(user_id, "awaiting_forecast_selection", data={"city": target_query_city})
        return True
    
# --- 用戶輸入城市名稱後，回覆該縣市的天數選單 ---
def reply_forecast_weather_of_city(api: ApiClient, reply_token: str, user_id: str, target_city: str) -> bool:
    """
    在用戶輸入特定城市後，回覆該城市的天數選擇 Flex Message。
    此函式會被 city_input_handler.py 中的 handle_awaiting_forecast_city_input 調用。
    """
    logger.info(f"[ForecastHandler] 用戶 {user_id} 輸入縣市 {target_city}，準備回覆該縣市的天數選單。")
    city_normalized = normalize_city_name(target_city)

    # 從資料庫獲取用戶的預設城市，用於在 Flex Message 中顯示；如果沒有設定，則顯示「未設定」
    default_user_city = get_default_city(user_id)
    default_display_city = normalize_city_name(default_user_city) if default_user_city else "未設定"

    # 檢查 default_display_city 的值
    logger.debug(f"[ForecastHandler] 用戶 {user_id} 的預設城市 (for display): {default_display_city}")

    # 建立並發送 Flex Message
    """
    根據傳入的 `target_city` 建立一個新的 Flex Message。
    `target_query_city` 參數被設定為用戶剛剛輸入的城市，保證當用戶從這個選單中選擇天數時，後續的查詢會針對該城市進行。
    """
    flex_message = create_forecast_options_flex_message(
        default_county=default_display_city, 
        target_query_city=city_normalized
    )

    # 檢查 Flex Message 是否成功建立並發送
    """
    檢查 `create_forecast_options_flex_message` 的回傳值是否有效。
    如果成功，就發送訊息並更新用戶狀態；如果失敗，則發送一個錯誤訊息，確保程式不會因 Flex Message 建立失敗而出錯。
    `set_user_state` 將用戶狀態更新為 `awaiting_forecast_selection`，確保後續的對話流程可以正確進行。
    """
    if flex_message:
        send_line_reply_message(api, reply_token, [flex_message])
        logger.info(f"[ForecastHandler] 成功回覆天數選單（針對指定城市 {city_normalized}）給 {user_id}。")
        # 設定用戶狀態，以便後續的 Postback 知道要查詢哪個城市
        set_user_state(user_id, "awaiting_forecast_selection", data={"city": city_normalized}) 
        return True
    else:
        logger.error(f"[ForecastHandler] create_forecast_options_flex_message 返回 None 或空。Flex Message 可能有問題。")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法載入該城市的天數選單，請稍候再試。")])
        return True