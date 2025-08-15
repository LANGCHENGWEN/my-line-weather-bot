# typhoon/area_hazard_api.py
"""
定義一個用於與中央氣象署（CWA）地區影響預警 API（ W-C0033-002）互動的客戶端類別 `AreaHazardApiClient`。
主要職責：
1. 封裝 API 請求：將對特定 CWA API 的 HTTP 請求細節（URL、參數、授權碼等）封裝在一個類別中，方便其他模組呼叫。
2. 處理 API 回應：從 API 取得 JSON 格式的原始資料後，檢查其成功狀態，並進行初步的數據結構驗證，確保資料是有效的。
3. 錯誤處理：使用 `try-except` 區塊處理在發送請求、接收回應或解析 JSON 過程中，可能發生的各種網路錯誤（如連線超時、HTTP 錯誤）或數據錯誤。
"""
import logging
import requests
from typing import Any, Dict, Optional
from config import CWA_TYPHOON_PROBABILITY_API

logger = logging.getLogger(__name__)

# --- 中央氣象署地區影響預警 API 客戶端，用於取得 W-C0033-002 天氣現象預警資料 ---
class AreaHazardApiClient:
    # --- 初始化 AreaHazardApiClient 類別 ---
    def __init__(self, authorization_code: str):
        """ 
        Args:
            authorization_code (str): 存取中央氣象署 API 所需的授權碼。
     
        Raises:
            ValueError: 如果授權碼為空。
        """
        # 初始化客戶端，設定基礎 URL 和授權碼
        # 將 `self.base_url` 和 `self.authorization_code` 作為類別的屬性，可以讓這些資訊在類別的其他方法（如 `fetch_area_hazard_raw_data`）中重複使用
        self.base_url = CWA_TYPHOON_PROBABILITY_API
        self.authorization_code = authorization_code

        # 檢查授權碼是否存在
        if not self.authorization_code:
            logger.error(
                "AreaHazardApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )
            raise ValueError(
                "AreaHazardApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )

    # --- 從 CWA W-C0033-002 API 獲取最新的地區影響預警原始資料 ---
    def fetch_area_hazard_raw_data(self) -> Optional[Dict[str, Any]]:
        """
        Returns:
            Optional[Dict[str, Any]]: 成功時返回 API 回應的 JSON 資料字典，失敗時返回 None。
        """
        params = {
            "Authorization": self.authorization_code,
            "format": "JSON"
        }
        
        try:
            # 向 CWA API 發送 HTTP GET 請求
            logger.info(f"嘗試從 CWA API ({self.base_url}) 獲取地區影響預警原始資料...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # 收到 4xx 或 5xx 的 HTTP 狀態碼時自動拋出異常

            data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構

            # 驗證 API 回應的成功狀態
            if not data or data.get("success") == "false":
                msg = data.get("message", "CWA API 回應表示請求失敗。")
                logger.warning(f"CWA API 回應失敗: {msg}")
                return None
            
            # 檢查 W-C0033-002 的實際數據在 records.record 列表下
            if 'records' not in data or 'record' not in data['records'] or not data['records']['record']:
                logger.info("CWA API 回應中未找到地區影響預警資料，或 'record' 列表為空。")
                return None

            logger.info(f"成功從 CWA 獲取 W-C0033-002 數據。Status: {response.status_code}")
            return data
              
        except requests.exceptions.HTTPError as e: # 捕獲並處理 HTTP 狀態碼錯誤
            logger.error(f"HTTP 錯誤發生: {e.response.status_code} - {e.response.text}", exc_info=True)
            return None
        except requests.exceptions.ConnectionError as e: # 捕獲並處理連線錯誤
            logger.error(f"連線錯誤發生: {e}", exc_info=True)
            return None
        except requests.exceptions.Timeout as e: # 捕獲並處理請求超時錯誤
            logger.error(f"請求超時 (timeout=10秒): {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e: # 捕獲並處理所有其他 requests 庫的錯誤
            logger.error(f"請求發生未知錯誤: {e}", exc_info=True)
            return None
        except (KeyError, IndexError) as e: # 捕獲並處理數據解析錯誤
            logger.error(f"解析 CWA API 回應時發生錯誤，可能資料結構不符: {e}", exc_info=True)
            return None
        except Exception as e: # 捕獲並處理所有未預期的錯誤
            logger.error(f"發生未預期的錯誤: {e}", exc_info=True)
            return None