# weather_today/today_uvindex_api.py
import json # 引入 json 模組以處理可能的 JSON 解析錯誤
import logging
import requests
from config import CWA_TODAY_UVINDEX_API
# from utils.text_processing import normalize_city_name

logger = logging.getLogger(__name__)

def get_today_uvindex_data(api_key: str, params: dict = None) -> dict | None:
    """
    執行對 CWB API 的通用請求。

    :param api_key: 您的中央氣象局開放資料平台授權碼。
    :param params: 額外的查詢參數 (字典形式)。
    :return: API 返回的 JSON 資料 (字典形式)，如果請求失敗則返回 None。
    """
    if not api_key:
        logger.error("API Key 未提供。請確保傳入有效的 API Key。")
        return None

    url = CWA_TODAY_UVINDEX_API

    default_params = {"Authorization": api_key, "format": "JSON"}
    if params:
        default_params.update(params)

    try:
        logger.info(f"正在向 CWB API 請求資料: {url} (Dataset ID: {url})")
        response = requests.get(url, params=default_params, timeout=10)
        response.raise_for_status()  # 檢查 HTTP 請求是否成功
        data = response.json()

        if data.get("success") != "true":
            error_msg = data.get("message", "API 返回 'success' 為 false。")
            logger.error(f"CWB API 請求失敗 (Dataset ID: {url}): {error_msg}")
            return None

        logger.info(f"成功獲取 Dataset ID: {url} 的資料。")
        return data
    
    except requests.exceptions.Timeout:
        logger.error(f"請求 CWB API 時發生連線超時錯誤 (Dataset ID: {url})。")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"請求 CWB API 時發生 HTTP 錯誤: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"請求 CWB API 時發生網路錯誤 (Dataset ID: {url}): {e}", exc_info=True)
        return None
    except ValueError as e:
        logger.error(f"解析 CWB API 回應時發生 JSON 解析錯誤 (Dataset ID: {url}): {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"解析 CWB API 回應時發生未知錯誤: {e}", exc_info=True)
        return None