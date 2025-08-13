# outfit_suggestion/outfit_responses.py
"""
處理和發送與穿搭建議功能相關的回覆訊息。
`reply_outfit_weather_of_city`函式會在接收到使用者指定的城市名稱後，動態生成一個包含「今日」、「即時」和「未來」三種穿搭建議選項的 Flex Message。
這個檔案將回覆訊息的內容建立邏輯與主處理器（outfit_handler.py）分離，使程式碼更具模組化和可維護性。
"""
import logging
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging.models import TextMessage

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import set_user_state, get_default_city

from outfit_suggestion.outfit_type_flex_messages import build_outfit_suggestions_flex

logger = logging.getLogger(__name__)

def reply_outfit_weather_of_city(api: ApiClient, reply_token: str, user_id: str, city_name: str) -> bool:
    """
    主要邏輯：接收使用者輸入的城市，並回覆該城市的穿搭建議主選單 (Flex Message)。
    輔助邏輯：先驗證城市名稱，然後根據使用者是否有預設城市，生成一個客製化的 Flex Message 選單，最後將這個選單發送給使用者。
    此函式也會更新使用者在 Firestore 中的狀態，以追蹤後續的互動。
    """
    try:
        logger.info(f"[OutfitResponses] 用戶 {user_id} 請求指定縣市 {city_name} 的穿搭建議選單。")

        city_normalized = normalize_city_name(city_name)
        default_user_city = get_default_city(user_id) # 從 Firestore 取得使用者之前設定的預設城市

        # --- 檢查使用者是否設定了預設城市，並根據情況提供一個預設顯示文字 ---
        # 確保即使在沒有預設城市的情況下，程式也不會因為 `None` 值而崩潰
        if default_user_city is not None:
            default_user_city_normalized = normalize_city_name(default_user_city)
        else:
            # 如果沒有預設城市，則使用這個預設顯示文字
            default_user_city_normalized = "您未設定預設城市，請先到設定選單中點選「切換預設城市」。"

        # 檢查 default_user_city_normalized 的值
        logger.debug(f"[OutfitResponses] 用戶 {user_id} 的預設城市 (from DB): {default_user_city_normalized}")

        # --- 負責調用 Flex Message 建立器，並將最終的 Flex Message 發送出去 ---
        """
        將使用者輸入的城市名稱和預設城市名稱作為參數傳遞給 `build_outfit_suggestions_flex`，讓 Flex Message 能夠根據這些資訊動態生成其內容（例如 Postback data 中包含的城市名稱）。
        檢查 Flex Message 是否成功建立，如果成功，則將訊息發送給使用者。
        更新使用者的狀態，以便在下一次互動時能夠知道使用者正在進行什麼操作。
        """
        flex_message = build_outfit_suggestions_flex(
            target_query_city=city_normalized,
            default_city_display=default_user_city_normalized
        )

        if flex_message:
            send_line_reply_message(api, reply_token, [flex_message])
            logger.info(f"[OutfitResponses] 成功回覆穿搭建議選單（針對指定城市 {city_normalized}）給 {user_id}。")
            set_user_state(user_id, "awaiting_outfit_selection", data={"city": city_normalized}) 
            return True # 如果成功發送訊息則返回 True，否則返回 False
        else:
            logger.error(f"[OutfitResponses] build_outfit_suggestions_flex 返回 None 或空。Flex Message 可能有問題。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法載入該城市的穿搭建議選單，請稍候再試。")])
            return False # Flex Message 建立失敗，返回 False
    
    # --- 處理通用的錯誤情況 ---
    except Exception as e:
        """
        這是一個健壯的錯誤處理機制。
        捕獲在 `try` 區塊中發生的任何未預期錯誤（例如 API 調用失敗或數據處理異常）。
        向使用者發送一個友善的通用錯誤訊息，這樣既有利於開發者除錯，又能保證使用者體驗不會因為系統崩潰而中斷。
        """
        logger.error(f"[OutfitResponses] 處理穿搭建議回覆時發生錯誤，用戶 {user_id}, 城市 {city_name}: {e}", exc_info=True)
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理您的請求時發生錯誤，請稍候再試。")])
        return False