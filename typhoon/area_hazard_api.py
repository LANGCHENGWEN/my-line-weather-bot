# typhoon/area_hazard_api.py
import os
import logging
import requests # 使用 requests 庫保持與 cwa_typhoon_api.py 一致
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

# 從你的 config.py 導入 API Key
# 假設 CWA_AREA_HAZARD_API_URL 也在 config.py 中定義了，或者直接寫在這裡
from config import CWA_TYPHOON_PROBABILITY_API # 假設你已在 config.py 中定義 CWA_AREA_HAZARD_API_URL

logger = logging.getLogger(__name__)

class AreaHazardApiClient:
    """
    中央氣象署地區影響預警 API 客戶端，用於取得 W-C0033-002 天氣現象預警資料。
    """
    def __init__(self, authorization_code: str):
        """
        初始化 AreaHazardApiClient。API 授權碼會從環境變數 CWA_API_KEY 讀取。
        並使用 config 中定義的 CWA_AREA_HAZARD_API_URL 作為基礎 URL。
        """
        self.base_url = CWA_TYPHOON_PROBABILITY_API
        self.authorization_code = authorization_code

        if not self.authorization_code:
            logger.error(
                "AreaHazardApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )
            raise ValueError(
                "AreaHazardApiClient 初始化錯誤：授權碼為空。請確認已傳入有效的中央氣象署 API 授權碼。"
            )

    def fetch_area_hazard_raw_data(self) -> Optional[Dict[str, Any]]:
        """
        從 CWA W-C0033-002 API 獲取最新的地區影響預警原始資料。
        """
        params = {
            "Authorization": self.authorization_code,
            "format": "JSON"
            # W-C0033-002 通常不需要 dataTime 和 limit/sort 參數，它返回的是當前的有效預警
        }
        
        try:
            logger.info(f"嘗試從 CWA API ({self.base_url}) 獲取地區影響預警原始資料...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # 對於 4xx/5xx 狀態碼拋出 HTTPStatusError

            data = response.json()

            if not data or data.get("success") == "false":
                msg = data.get("message", "CWA API 回應表示請求失敗。")
                logger.warning(f"CWA API 回應失敗: {msg}")
                return None
            
            # W-C0033-002 的實際數據在 records.record 列表下
            if 'records' not in data or 'record' not in data['records'] or not data['records']['record']:
                logger.info("CWA API 回應中未找到地區影響預警資料，或 'record' 列表為空。")
                return None

            logger.info(f"成功從 CWA 獲取 W-C0033-002 數據。Status: {response.status_code}")
            return data
            
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
# 如果需要在本地獨立測試這個檔案
if __name__ == "__main__":
    # 確保你的 config.py 中有 CWA_API_KEY 和 CWA_AREA_HAZARD_API_URL
    # 為了測試，這裡假設一個假的 API KEY，實際請用你自己的
    # from config import CWA_API_KEY as TEST_API_KEY # 這樣引入更明確
    # 如果沒有 config.py 則直接定義
    TEST_API_KEY = os.getenv("CWA_API_KEY", "YOUR_CWA_API_KEY_HERE") # 從環境變數獲取或手動填入
    # TEST_AREA_HAZARD_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-002" # 如果 config.py 中沒有定義

    # 配置 logging 以便在測試時看到輸出
    logging.basicConfig(level=logging.INFO)

    print("正在初始化 AreaHazardApiClient...")
    try:
        api_client = AreaHazardApiClient(TEST_API_KEY)
        print("正在獲取地區影響預警數據...")
        data = api_client.fetch_area_hazard_raw_data()
        if data:
            print(f"成功獲取數據，部分記錄數: {len(data['records']['record'])}")
            if len(data['records']['record']) > 0:
                first_record = data['records']['record'][0]
                print(f"第一個預警類型: {first_record.get('datasetInfo', {}).get('datasetDescription')}")
                print(f"第一個預警內容 (部分): {first_record.get('contents', {}).get('content', {}).get('contentText', '')[:100]}...")
        else:
            print("未能獲取地區影響預警數據。")
    except ValueError as e:
        print(f"初始化錯誤: {e}")
    except Exception as e:
        print(f"測試時發生錯誤: {e}")
"""