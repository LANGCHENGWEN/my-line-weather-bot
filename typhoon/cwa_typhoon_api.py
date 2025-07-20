# typhoon/cwa_typhoon_api.py
# 這個檔案負責與中央氣象署的颱風 API 進行溝通，獲取原始數據
import os
import logging
import requests
from config import CWA_TYPHOON_WARNING_API
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class TyphoonApiClient:
    """
    中央氣象署颱風 API 客戶端，用於取得 W-C0034-005 颱風警報相關資料。
    """
    def __init__(self, authorization_code: str):
        """
        初始化 TyphoonApiClient。API 授權碼會從環境變數 CWA_API_AUTHORIZATION_CODE 讀取。
        並使用 config 中定義的 CWA_TYPHOON_WARNING_API 作為基礎 URL。
        """
        self.base_url = CWA_TYPHOON_WARNING_API
        self.authorization_code = authorization_code

        if not self.authorization_code:
            logger.error(
                "TyphoonApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )
            raise ValueError(
                "TyphoonApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )

    def _format_time_for_api(self, dt_obj: datetime) -> str:
        """
        將 datetime 物件格式化為 API 所需的 ISO 8601 格式 (YYYY-MM-DDThh:mm:ss)。
        API 預期的是 UTC+8 時間。
        """
        cst_tz = timezone(timedelta(hours=8))
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=cst_tz)
        else:
            dt_obj = dt_obj.astimezone(cst_tz)
        return dt_obj.isoformat(timespec='seconds')

    def fetch_typhoon_raw_data(self) -> Optional[Dict[str, Any]]:
        """
        從 CWA API 獲取最新的颱風原始資料。
        """
        params = {
            "Authorization": self.authorization_code,
            "format": "JSON",
            "dataTime": self._format_time_for_api(datetime.now() - timedelta(hours=48)),
            "limit": 20, # 限制返回筆數，提高效率
            "sort": "dataTime" # 依據發布時間排序
        }

        try:
            logger.info(f"嘗試從 CWA API ({self.base_url}) 獲取颱風原始資料...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # 如果狀態碼不是 200，則拋出 HTTPError

            data = response.json()

            if not data or data.get("success") == "false":
                msg = data.get("message", "CWA API 回應表示請求失敗。")
                logger.warning(f"CWA API 回應失敗: {msg}")
                return None
            
            typhoon_list = data.get("records", {}).get("tropicalCyclones", {}).get("tropicalCyclone", [])

            if not typhoon_list:
                logger.info("CWA API 回應中未找到颱風資料，或 'tropicalCyclone' 列表為空。")
                return None

            # 找出最新發布時間的颱風資料
            latest_typhoon_data = None
            latest_data_time = None

            for typhoon_entry in typhoon_list:
                if "analysisData" in typhoon_entry and "fix" in typhoon_entry["analysisData"]:
                    analysis_fixes = typhoon_entry["analysisData"]["fix"]
                    for fix_entry in analysis_fixes:
                        current_fix_time_str = fix_entry.get("fixTime")
                        if current_fix_time_str:
                            try:
                                # === 核心修改點 2：調整日期時間解析格式為 ISO 8601 ===
                                # fromisoformat 可以處理帶有時區的 ISO 8601 格式
                                current_fix_time = datetime.fromisoformat(current_fix_time_str)
                                
                                if latest_data_time is None or current_fix_time > latest_data_time:
                                    latest_data_time = current_fix_time
                                    latest_typhoon_data = typhoon_entry
                            except ValueError:
                                logger.warning(f"無法解析颱風資料中的 fixTime: {current_fix_time_str}", exc_info=True)
                                continue

            if latest_typhoon_data:
                logger.info(f"成功取得最新颱風資料：{latest_typhoon_data.get('typhoonName', '未知颱風')} (最新測報時間: {latest_data_time.isoformat() if latest_data_time else 'N/A'})")
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

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 錯誤發生: {e.response.status_code} - {e.response.text}", exc_info=True)
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"連線錯誤發生: {e}", exc_info=True)
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"請求超時 (timeout=10秒): {e}", exc_info=True)
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"請求發生未知錯誤: {e}", exc_info=True)
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"解析 CWA API 回應時發生錯誤，可能資料結構不符: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"發生未預期的錯誤: {e}", exc_info=True)
            return None

"""
# 範例使用 (取消註解可進行測試)
if __name__ == "__main__":
    # 請在執行前設定環境變數: export CWA_API_AUTHORIZATION_CODE="YOUR_CWA_API_KEY"
    # os.environ["CWA_API_AUTHORIZATION_CODE"] = "YOUR_CWA_API_KEY" # 僅供測試，生產環境請用實際環境變數

    try:
        api_client = TyphoonApiClient()
        raw_data = api_client.fetch_typhoon_raw_data()
        if raw_data:
            print("\n--- 獲取到的原始颱風資料 (部分內容) ---")
            print(f"颱風名稱: {raw_data.get('typhoonName')}")
            print(f"觀測時間: {raw_data.get('dataTime')}")
            if raw_data.get("forecastData") and raw_data["forecastData"].get("fix"):
                print(f"預報點數量: {len(raw_data['forecastData']['fix'])}")
            else:
                print("無預報點資料。")
        else:
            print("無法獲取颱風原始資料。")
    except ValueError as ve:
        print(f"設定錯誤: {ve}")
    except Exception as e:
        print(f"測試執行錯誤: {e}")
"""