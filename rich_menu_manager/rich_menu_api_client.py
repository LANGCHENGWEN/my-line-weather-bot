# rich_menu_manager/rich_menu_api_client.py
import os
import logging
# import requests

from linebot.v3.messaging import (
    MessagingApi, MessagingApiBlob, Configuration, RichMenuRequest,
    ApiException, CreateRichMenuAliasRequest, UpdateRichMenuAliasRequest
)
from linebot.v3.messaging.models import RichMenuListResponse

logger = logging.getLogger(__name__)

LINE_BLOB_API_BASE_URL = "https://api-data.line.me"

# --- LINE Rich Menu API 實際操作 ---

def create_rich_menu_on_line(line_bot_api: MessagingApi, rich_menu_request_obj: RichMenuRequest) -> str | None:
    """在 LINE 平台創建 Rich Menu 並返回 ID."""
    try:
        response = line_bot_api.create_rich_menu(rich_menu_request_obj)
        logger.info(f"Rich Menu 創建成功, ID: {response.rich_menu_id}")
        return response.rich_menu_id
    except Exception as e:
        logger.error(f"創建 Rich Menu 失敗: {e}", exc_info=True)
        return None

def upload_rich_menu_image_to_line(line_blob_api: MessagingApiBlob, rich_menu_id: str, image_path: str) -> bool:
    """
    上傳 Rich Menu 圖片到 LINE 伺服器。
    Args:
        line_blob_api (MessagingApiBlob): MessagingApiBlob 實例。
        rich_menu_id (str): 要上傳圖片的 Rich Menu ID。
        image_path (str): 本地圖片檔案的路徑。
    """
    # 檢查圖片檔案是否存在
    if not os.path.exists(image_path):
        logger.error(f"Rich Menu 圖片檔案不存在: {image_path}")
        return False
    
    # 根據圖片擴展名判斷 Content-Type
    file_extension = os.path.splitext(image_path)[1].lower()
    content_type = None
    if file_extension == ".png":
        content_type = "image/png"
    elif file_extension in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    else:
        logger.error(f"不支援的圖片格式: {image_path}")
        return False
    
    if content_type is None: # 確保有 content_type
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
                'Authorization': f'Bearer {channel_access_token}' # <-- CRITICAL CHANGE HERE: 加入 Authorization 頭
            }

            # logger.debug(f"Calling set_rich_menu_image with args: rich_menu_id={rich_menu_id}, content_type={content_type}, file_object={f}")
            logger.debug(f"Calling api_client.request for image upload with rich_menu_id={rich_menu_id}, content_type={content_type}, img_bytes_len={len(img_bytes)}")

            response = line_blob_api.api_client.request(
                method=method,
                url=full_url,
                headers=headers, # 直接在 headers 中指定 Content-Type
                body=img_bytes # 直接傳遞二進制數據作為請求體
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

def create_or_update_rich_menu_alias_on_line(line_bot_api: MessagingApi, rich_menu_id: str, alias: str) -> bool:
    """為 Rich Menu 創建或更新別名."""
    try:
        # 使用 CreateRichMenuAliasRequest 構建請求物件
        create_request = CreateRichMenuAliasRequest(
            rich_menu_id=rich_menu_id,
            rich_menu_alias_id=alias
        )
        line_bot_api.create_rich_menu_alias(create_rich_menu_alias_request=create_request)
        logger.info(f"Rich Menu 別名 '{alias}' 成功連結到 ID: {rich_menu_id}")
        return True
    except ApiException as e: # <--- 針對 ApiException 進行處理
        # 檢查是否是「別名已存在」的錯誤 (HTTP 400 Bad Request with specific message)
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
        else:
            # 如果不是別名衝突，仍然記錄原始錯誤
            logger.error(f"創建 Rich Menu 別名 '{alias}' 失敗 (ApiException): {e}", exc_info=True)
            return False
    except Exception as e:
        logger.error(f"創建 Rich Menu 別名 '{alias}' 失敗: {e}", exc_info=True)
        return False

def set_default_rich_menu_on_line(line_bot_api: MessagingApi, rich_menu_id: str) -> bool:
    """設定預設 Rich Menu."""
    try:
        line_bot_api.set_default_rich_menu(rich_menu_id)
        logger.info(f"Rich Menu ID: {rich_menu_id} 已設為預設。")
        return True
    except Exception as e:
        logger.error(f"設定預設 Rich Menu 失敗: {e}", exc_info=True)
        return False

def get_current_default_rich_menu_id_from_line(line_bot_api: MessagingApi) -> str | None:
    """從 LINE 獲取當前預設 Rich Menu ID."""
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

def delete_all_rich_menus_on_line(line_bot_api: MessagingApi):
    """刪除 LINE 平台上所有 Rich Menu."""
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