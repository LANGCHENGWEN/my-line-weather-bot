# typhoon/cwa_typhoon_api.py
"""
獲取「中央氣象署颱風警報 API」(W-C0034-005) 的原始數據。
主要職責：
1. 封裝 API 請求：提供一個 `TyphoonApiClient` 類別，將複雜的 HTTP 請求細節（如 URL、參數、授權碼等）隱藏在一個簡單的函式呼叫中。
2. 處理 API 錯誤：對可能發生的各種網路錯誤（連線失敗、超時、HTTP 錯誤碼）和 API 回應錯誤進行捕獲與記錄，確保程式在發生問題時不會直接崩潰，而是返回一個友好的 None 值。
3. 數據過濾與精簡：API 返回的資料可能包含多個颱風的多筆歷史紀錄，這個模組會從中自動篩選出「最新發布」的那一筆颱風資料，並整理為一個單一的字典，減少下游模組的處理負擔。
4. 時間格式化：將 Python 的 `datetime` 物件轉換為 API 所要求的特定時間格式，確保請求的準確性。
"""
import logging
import requests
from typing import Any, Dict, Optional
from config import CWA_TYPHOON_WARNING_API
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# --- 中央氣象署颱風 API 客戶端，用於取得 W-C0034-005 颱風警報相關資料 ---
class TyphoonApiClient:
    # --- 初始化 TyphoonApiClient 類別 ---
    def __init__(self, authorization_code: str):
        """ 
        Args:
            authorization_code (str): 存取中央氣象署 API 所需的授權碼。
     
        Raises:
            ValueError: 如果授權碼為空。
        """
        # 初始化客戶端，設定基礎 URL 和授權碼
        # 將 `self.base_url` 和 `self.authorization_code` 作為類別的屬性，可以讓這些資訊在類別的其他方法（如 `fetch_typhoon_raw_data`）中重複使用
        self.base_url = CWA_TYPHOON_WARNING_API
        self.authorization_code = authorization_code

        # 檢查授權碼是否存在
        if not self.authorization_code:
            logger.error(
                "TyphoonApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )
            raise ValueError(
                "TyphoonApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )

    # --- 將 datetime 物件格式化為 API 所需的 ISO 8601 格式 (YYYY-MM-DDThh:mm:ss) ---
    def _format_time_for_api(self, dt_obj: datetime) -> str:
        """
        API 預期的是 UTC+8 時間。
        這個輔助函式確保所有傳送給 API 的時間參數都符合其嚴格的格式要求。
        - 統一時間格式：將時間格式化的邏輯封裝在一個私有方法中，確保所有時間相關的 API 參數都以一致的方式處理，避免重複程式碼。
        - 時區處理：中央氣象署的 API 通常使用台灣標準時間（UTC+8），這段程式碼會將任何傳入的 `datetime` 物件轉換為 UTC+8 時區，然後再進行格式化，確保時間參數的準確性。
        - 防禦性設計：檢查傳入的 `datetime` 物件是否帶有時區資訊，並進行相應的處理，增加函式的健壯性。
        """
        cst_tz = timezone(timedelta(hours=8))
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=cst_tz)
        else:
            dt_obj = dt_obj.astimezone(cst_tz)
        return dt_obj.isoformat(timespec='seconds')

    # --- 從 CWA API 獲取 W-C0034-005 最新的颱風原始資料 ---
    def fetch_typhoon_raw_data(self) -> Optional[Dict[str, Any]]:
        """
        執行整個 API 請求和初步數據處理的流程。
        首先會構建請求參數，接著發送 HTTP 請求，然後檢查回應狀態碼和內容。
        最後從可能包含多筆記錄的回應中，篩選出最新的一筆颱風資料並返回。
        """
        # 設定 API 請求參數
        params = {
            "Authorization": self.authorization_code, # 使用在 `__init__` 中設定的授權碼，這是 API 認證的關鍵
            "format": "JSON", # 指定回傳的資料格式為 JSON
            "dataTime": self._format_time_for_api(datetime.now() - timedelta(hours=48)), # 篩選在特定時間之後發布的資料
            "limit": 20, # 限制返回筆數，提高效率
            "sort": "dataTime" # 依據發布時間排序
        }

        try:
            # 發送 HTTP 請求並處理回應
            logger.info(f"嘗試從 CWA API ({self.base_url}) 獲取颱風原始資料...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # 當 HTTP 回應的狀態碼是 4xx 或 5xx 時，自動拋出 HTTPError

            data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構

            # 驗證 API 回應的成功狀態
            if not data or data.get("success") == "false":
                msg = data.get("message", "CWA API 回應表示請求失敗。")
                logger.warning(f"CWA API 回應失敗: {msg}")
                return None
            
            # 提取並尋找最新的颱風資料
            """
            API 回應的資料結構可能包含多個颱風，每個颱風可能有多次的測報紀錄。
            從這個複雜的結構中，找出「最新」的那一筆紀錄。
            - 數據精簡：只需要最新的颱風資訊來回覆用戶，因此透過遍歷所有回傳的紀錄，比較每個紀錄中的 `fixTime`，就能找到最新的一筆。
            - 防禦性程式設計：使用多層的 `.get()` 方法來安全的訪問巢狀字典，避免因 API 結構偶爾不一致而導致 `KeyError`。
            - 統一輸出格式：找到最新的紀錄後，重新封裝回一個與原始 API 結構相似的字典中，但只包含一筆最新的颱風資料。
              下游的解析器可以繼續使用相同的邏輯來處理數據，而不需要為單一紀錄的情況做特殊處理。
            """
            # 層層尋找並取出颱風的列表，檢查 typhoon_list 列表是否為空
            typhoon_list = data.get("records", {}).get("tropicalCyclones", {}).get("tropicalCyclone", [])
            if not typhoon_list:
                logger.info("CWA API 回應中未找到颱風資料，或 'tropicalCyclone' 列表為空。")
                return None

            # 找出最新發布時間的颱風資料
            latest_typhoon_data = None
            latest_data_time = None

            # 遍歷所有回傳的紀錄，並比較每個紀錄中的 `fixTime`
            for typhoon_entry in typhoon_list:
                if "analysisData" in typhoon_entry and "fix" in typhoon_entry["analysisData"]:
                    analysis_fixes = typhoon_entry["analysisData"]["fix"]
                    for fix_entry in analysis_fixes:
                        current_fix_time_str = fix_entry.get("fixTime")
                        if current_fix_time_str:
                            try:
                                current_fix_time = datetime.fromisoformat(current_fix_time_str)
                                if latest_data_time is None or current_fix_time > latest_data_time:
                                    latest_data_time = current_fix_time
                                    latest_typhoon_data = typhoon_entry
                            except ValueError:
                                logger.warning(f"無法解析颱風資料中的 fixTime: {current_fix_time_str}", exc_info=True)
                                continue

            # 封裝回一個與原始 API 結構相似的字典中，但只包含一筆最新的颱風資料
            if latest_typhoon_data:
                logger.info(f"成功取得最新颱風資料：{latest_typhoon_data.get('typhoonName', '未知颱風')} (最新測報時間: {latest_data_time.isoformat() if latest_data_time else '未知時間'})")
                return {
                    "records": {
                        "tropicalCyclones": {
                            "tropicalCyclone": [latest_typhoon_data]
                        }
                    }
                }
            else:
                logger.info("在所有篩選出的資料中，未找到有效的最新測報點。")
                return None

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