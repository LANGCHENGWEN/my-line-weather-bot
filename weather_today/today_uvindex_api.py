# weather_today/today_uvindex_api.py
"""
與中央氣象署「紫外線指數」API 的互動。
主要職責：
1. API 請求：根據預設的 API URL 和提供的授權金鑰，發送 HTTP GET 請求。
2. 參數管理：合併額外的查詢參數，使函式具有彈性，可以根據需要篩選資料。
3. 錯誤處理：捕捉並處理各種可能的錯誤，包括無效的 API 金鑰、網路問題、伺服器錯誤以及 JSON 解析失敗等。
4. 資料回傳：成功獲取並驗證資料後，以 Python 字典的形式回傳，供其他模組使用；如果發生任何錯誤，則返回 None。
"""
import logging
import requests
from config import CWA_TODAY_UVINDEX_API

logger = logging.getLogger(__name__)

def get_today_uvindex_data(api_key: str, params: dict = None) -> dict | None:
    """
    執行對中央氣象署紫外線指數 API 的通用請求。
    獲取紫外線指數資料的單一入口，負責發送請求、合併參數、處理所有可能的錯誤情況。
    """
    # 檢查是否提供有效的 `api_key`
    if not api_key:
        logger.error("API Key 未提供。請確保傳入有效的 API Key。")
        return None

    # --- 設置 API URL ---
    url = CWA_TODAY_UVINDEX_API

    # --- 準備 API 請求參數 ---
    default_params = {"Authorization": api_key, "format": "JSON"}
    # 如果呼叫者傳入額外的 `params`，程式會使用 `.update()` 方法將這些參數合併進 `default_params`
    if params:
        default_params.update(params)

    # --- 發送請求與錯誤處理 ---
    try:
        logger.info(f"正在向 CWA API 請求資料: {url} (Dataset ID: {url})")
        # 發送 HTTP GET 請求
        # `timeout=10` 設置超時時間，防止程式因網路延遲而卡住
        response = requests.get(url, params=default_params, timeout=10)
        response.raise_for_status()  # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`
        
        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構

        # 驗證 API 回應的成功狀態
        if data.get("success") != "true":
            error_msg = data.get("message", "API 返回 'success' 為 false。")
            logger.error(f"CWA API 請求失敗 (Dataset ID: {url}): {error_msg}")
            return None

        logger.info(f"成功獲取 Dataset ID: {url} 的資料。")
        return data
    
    except requests.exceptions.Timeout:
        logger.error(f"請求 CWA API 時發生連線超時錯誤 (Dataset ID: {url})。")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"請求 CWA API 時發生 HTTP 錯誤: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"請求 CWA API 時發生網路錯誤 (Dataset ID: {url}): {e}", exc_info=True)
        return None
    except ValueError as e:
        logger.error(f"解析 CWA API 回應時發生 JSON 解析錯誤 (Dataset ID: {url}): {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"解析 CWA API 回應時發生未知錯誤: {e}", exc_info=True)
        return None