# rich_menu_manager/rich_menu_api_client.py
"""
作為一個封裝層，專門處理與 LINE Rich Menu API 的所有底層互動。
提供一系列函式，可以更簡潔的執行各種操作：
1. 在 LINE 平台上創建新的 Rich Menu，並獲取其 ID。
2. 上傳 Rich Menu 的圖片素材到 LINE 伺服器。
3. 為 Rich Menu 建立或更新別名，這是實現 Rich Menu 動態切換的關鍵。
4. 設定預設的 Rich Menu，確保所有新用戶或未指定別名的用戶都能看到 Rich Menu。
5. 獲取當前預設的 Rich Menu ID。
6. 刪除所有現有的 Rich Menu，這在部署新 Rich Menu 或清理環境時非常有用。
"""
import os
import logging

from linebot.v3.messaging import (
    MessagingApi, MessagingApiBlob, RichMenuRequest,
    ApiException, CreateRichMenuAliasRequest, UpdateRichMenuAliasRequest
)
from linebot.v3.messaging.models import RichMenuListResponse

logger = logging.getLogger(__name__)

LINE_BLOB_API_BASE_URL = "https://api-data.line.me"

# --- 在 LINE 平台上創建 Rich Menu 並返回唯一的 ID ---
def create_rich_menu_on_line(line_bot_api: MessagingApi, rich_menu_request_obj: RichMenuRequest) -> str | None:
    """
    接收一個已配置好尺寸、區域和動作的 Rich Menu 請求物件 (rich_menu_request_obj)。
    透過 MessagingApi 實例向 LINE 伺服器發送創建請求。
    成功時，會記錄日誌並返回新創建的 Rich Menu ID。
    失敗時，會捕獲異常並記錄錯誤日誌，然後返回 None。
    """
    try:
        response = line_bot_api.create_rich_menu(rich_menu_request_obj)
        logger.info(f"Rich Menu 創建成功, ID: {response.rich_menu_id}")
        return response.rich_menu_id
    except Exception as e:
        logger.error(f"創建 Rich Menu 失敗: {e}", exc_info=True)
        return None

# --- 上傳 Rich Menu 圖片到 LINE 伺服器 ---
def upload_rich_menu_image_to_line(line_blob_api: MessagingApiBlob, rich_menu_id: str, image_path: str) -> bool:
    """
    在執行上傳操作之前，會先檢查本地的圖片檔案是否存在。
    如果檔案路徑錯誤或檔案不存在，直接呼叫 `open()` 會導致 `FileNotFoundError`，而且 LINE API 的請求也會因為沒有內容而失敗。
    通過預先檢查，可以在程式進入更複雜的網路請求流程之前，快速捕捉到這種常見錯誤，並立即返回，避免不必要的資源浪費，提高函式的健壯性。
    """
    if not os.path.exists(image_path): # 檢查圖片檔案是否存在
        logger.error(f"Rich Menu 圖片檔案不存在: {image_path}")
        return False
    
    # 根據圖片檔案的副檔名來判斷 Content-Type
    """
    LINE API 在上傳 Rich Menu 圖片時，要求在 HTTP 請求的 `Content-Type` 標頭中明確指定圖片的類型（例如 `image/png` 或 `image/jpeg`）。
    透過檢查副檔名，可以動態的設定這個必要的標頭。
    如果副檔名不是支援的類型，程式會立即記錄錯誤並返回 `False`，這樣可以避免發送一個註定會失敗的 API 請求。
    """
    file_extension = os.path.splitext(image_path)[1].lower()
    content_type = None
    if file_extension == ".png":
        content_type = "image/png"
    elif file_extension in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    else:
        logger.error(f"不支援的圖片格式: {image_path}")
        return False
    
    if content_type is None:
        logger.error(f"無法確定圖片 {image_path} 的 Content-Type。")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            img_bytes = f.read()

            full_url = f"{LINE_BLOB_API_BASE_URL}/v2/bot/richmenu/{rich_menu_id}/content"
            method = "POST"

            channel_access_token = line_blob_api.api_client.configuration.access_token

            # 構建 headers，包含 Content-Type 和 Authorization
            headers = {
                'Content-Type': content_type,
                'Authorization': f'Bearer {channel_access_token}'
            }

            logger.debug(f"呼叫 api_client.request 使用 rich_menu_id={rich_menu_id} 進行圖片上傳, content_type={content_type}, img_bytes_len={len(img_bytes)}")

            response = line_blob_api.api_client.request(
                method=method,
                url=full_url,
                headers=headers, # 直接在 headers 中指定 Content-Type
                body=img_bytes   # 直接傳遞二進制數據作為請求體
            )

            # 檢查 HTTP 狀態碼
            if 200 <= response.status < 300:
                logger.info(f"Rich Menu 圖片 {image_path} 上傳成功。")
                return True
            else:
                logger.error(f"上傳 Rich Menu 圖片 {image_path} 失敗 (HTTP Status: {response.status}, Body: {response.data})")
                return False
        
    except ApiException as e:
        logger.error(f"上傳 Rich Menu 圖片 {image_path} 失敗 (API Error): {e}", exc_info=True)
        return False # 上傳失敗返回 False
    except Exception as e: # 捕獲過程中其他意料之外的錯誤
        logger.error(f"上傳 Rich Menu 圖片 {image_path} 時發生未知錯誤: {e}", exc_info=True)
        return False

# --- 為 Rich Menu 創建或更新別名 ---
def create_or_update_rich_menu_alias_on_line(line_bot_api: MessagingApi, rich_menu_id: str, alias: str) -> bool:
    """
    嘗試為一個 Rich Menu 創建一個別名。
    如果別名已經存在（這會導致一個 ApiException），會捕獲這個錯誤，並自動切換到更新模式，將現有的別名重新指向新的 Rich Menu ID。
    """
    try:
        # 先嘗試創建一個新的 Rich Menu 別名，因為在大多數情況下，別名可能尚未創建
        create_request = CreateRichMenuAliasRequest(
            rich_menu_id=rich_menu_id,
            rich_menu_alias_id=alias
        )
        line_bot_api.create_rich_menu_alias(create_rich_menu_alias_request=create_request)
        logger.info(f"Rich Menu 別名 '{alias}' 成功連結到 ID: {rich_menu_id}")
        return True
    except ApiException as e:
        """
        如果創建失敗，會檢查錯誤是否為「別名已存在」的衝突錯誤。
        如果是別名衝突，不應該將其視為一個致命錯誤，而是應該將其視為一個已存在的別名，需要進行「更新」操作。
        這種設計讓整個流程更具彈性，不論是首次創建還是後續更新，呼叫同一個函式都能達到將別名指向正確 Rich Menu 的目的。
        """
        if e.status == 400 and "conflict richmenu alias id" in e.body.lower():
            logger.warning(f"Rich Menu 別名 '{alias}' 已存在，嘗試更新。")
            try:
                update_request_body = UpdateRichMenuAliasRequest(
                    rich_menu_id=rich_menu_id
                )
                line_bot_api.update_rich_menu_alias(
                    rich_menu_alias_id=alias,
                    update_rich_menu_alias_request=update_request_body
                )
                logger.info(f"Rich Menu 別名 '{alias}' 已成功更新，連結到 ID: {rich_menu_id}")
                return True
            except Exception as update_e:
                logger.error(f"更新 Rich Menu 別名 '{alias}' 失敗: {update_e}", exc_info=True)
                return False
        else: # 如果不是別名衝突，仍然記錄原始錯誤
            logger.error(f"創建 Rich Menu 別名 '{alias}' 失敗 (ApiException): {e}", exc_info=True)
            return False
    except Exception as e:
        logger.error(f"創建 Rich Menu 別名 '{alias}' 失敗: {e}", exc_info=True)
        return False

# --- 設定預設 Rich Menu ---
def set_default_rich_menu_on_line(line_bot_api: MessagingApi, rich_menu_id: str) -> bool:
    """
    直接呼叫 LINE Messaging API 的 `set_default_rich_menu` 方法，將指定的 Rich Menu ID 設為所有用戶的預設 Rich Menu。
    成功或失敗都會記錄相應的日誌，並返回 True 或 False。
    """
    try:
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info(f"Rich Menu ID: {rich_menu_id} 已設為預設。")
        return True
    except Exception as e:
        logger.error(f"設定預設 Rich Menu 失敗: {e}", exc_info=True)
        return False

# --- 從 LINE 平台獲取當前預設 Rich Menu 的 ID ---
def get_current_default_rich_menu_id_from_line(line_bot_api: MessagingApi) -> str | None:
    """
    用於在部署新 Rich Menu 前，確認當前預設 Rich Menu 的狀態，避免重複設定或意外修改。
    處理 API 返回的各種情況，包括沒有設定任何預設 Rich Menu 的情況（API 會返回 404 錯誤）。
    """
    try:
        response = line_bot_api.get_default_rich_menu()
        if hasattr(response, 'rich_menu_id'):
            return response.rich_menu_id
        return None
    except ApiException as e:
        if e.status == 404:
            logger.info("目前沒有設定預設 Rich Menu。")
        else:
            logger.error(f"獲取預設 Rich Menu 失敗: {e}", exc_info=True)
        return None

# --- 刪除 LINE 平台上所有已註冊的 Rich Menu ---
def delete_all_rich_menus_on_line(line_bot_api: MessagingApi):
    """
    先呼叫 `get_rich_menu_list()` 來獲取所有 Rich Menu 的列表。
    接著遍歷這個列表，並對於每一個 Rich Menu ID 呼叫 `delete_rich_menu()` 方法，進行逐一刪除。
    這個函式主要用於開發和測試環境的清理工作，確保每次部署時都是乾淨的狀態，避免 Rich Menu 混亂。
    """
    try:
        rich_menu_list_response: RichMenuListResponse = line_bot_api.get_rich_menu_list()
        rich_menus = rich_menu_list_response.richmenus
        if not rich_menus:
            logger.info("目前沒有任何 Rich Menu 可以刪除。")
            return

        for rich_menu in rich_menus:
            if hasattr(rich_menu, 'rich_menu_id'):
                line_bot_api.delete_rich_menu(rich_menu.rich_menu_id)
                logger.info(f"已刪除 Rich Menu: {rich_menu.rich_menu_id}")
            else:
                logger.warning(f"偵測到非預期的 Rich Menu 物件類型，無法刪除: {type(rich_menu)} - {rich_menu}")
        logger.info("所有 Rich Menu 已被刪除。")
    except Exception as e:
        logger.error(f"刪除所有 Rich Menu 失敗: {e}", exc_info=True)