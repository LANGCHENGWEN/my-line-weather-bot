# weather_today/cwa_today_api.py
"""
與中央氣象署的「未來 36 小時天氣預報」API 進行互動。
主要職責：
1. 發送請求：根據給定的 API 金鑰和地點名稱，向氣象署的指定 API 發出 HTTP GET 請求。
2. 參數設定：在發送請求前，處理並正規化地點名稱，並設定只獲取需要的特定氣象元素（如天氣現象、溫度等）。
3. 錯誤處理：處理各種可能發生的錯誤，包括連線超時、網路問題、無效的 HTTP 狀態碼，以及 API 回應中數據不完整或格式錯誤等情況。
4. 回傳資料：如果所有過程都成功，將 API 回傳的 JSON 數據解析成 Python 字典並回傳；否則回傳 None，讓呼叫者知道請求失敗。
"""
import logging
import requests
from config import CWA_FORECAST_36HR_API
from utils.text_processing import normalize_city_name

logger = logging.getLogger(__name__)

def get_cwa_today_data(api_key: str, location_name: str) -> dict | None:
    """
    從中央氣象署 F-C0032-001 取得指定縣市的今明 36 小時天氣預報資料。
    獲取今日天氣資料的入口點，將 API 呼叫的邏輯封裝在一個獨立的單元中，處理從發送請求、驗證回應到處理各種錯誤的所有環節。
    最終回傳一個原始的 JSON 字典，供其他模組進一步解析。
    """
    # --- 設置 API URL ---
    url = CWA_FORECAST_36HR_API

    # --- 對輸入的縣市名稱進行標準化 ---
    # 確保與 API 接受的格式相符（例如將「台中市」轉換為「臺中市」）
    # 設定發送到 API 的所有查詢參數，包括授權金鑰、回應格式和特定氣象元素
    query_location_name = normalize_city_name(location_name)
    logger.debug(f"標準化後的 location_name: '{query_location_name}'")

    # --- 準備 API 請求參數 ---
    params = {
        "Authorization" : api_key,
        "format"        : "JSON",
        "locationName"  : [query_location_name],
        "elementName"   : ["Wx", "PoP", "MinT", "MaxT", "CI"] # 取得天氣現象, 降雨機率, 最低溫, 最高溫, 舒適度
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}")

    # --- 發送請求與錯誤處理 ---
    try:
        logger.info(f"正在從中央氣象署 API ({CWA_FORECAST_36HR_API}) 取得 {location_name} 的今日天氣資料..")
        # 使用 `requests` 函式庫發送 HTTP GET 請求
        # `timeout=10` 設置超時時間，防止程式因網路延遲而卡住
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`

        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")

        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構
        
        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 驗證 API 回應的成功狀態
        if data.get("success") != "true":
            logger.warning(f"CWA API 回應 'success' 為 False，未能成功取得資料。回應內容: {data.get('message', '無訊息')}")
            return None

        # 檢查 'location' 數據是否存在
        if not data.get("records", {}).get("location"):
            logger.warning(f"從中央氣象署 API 成功取得回應，但 {location_name} 的 'location' 數據為空或不存在。")
            return None
        
        # 如果以上檢查都通過，則正常返回 data
        logger.info(f"成功取得並驗證 {location_name} 的今日天氣資料。")
        return data

    except requests.exceptions.Timeout:
        logger.error(f"從中央氣象署 API 取得今日天氣資料時發生連線超時錯誤。")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"從中央氣象署 API 取得今日天氣資料時發生 HTTP 錯誤: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"從中央氣象署 API 取得今日天氣資料時發生網路錯誤: {e}", exc_info=True)
        return None
    except ValueError as e:
        logger.error(f"解析中央氣象署今日天氣 API 回應時發生 JSON 解析錯誤: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"取得中央氣象署今日天氣資料時發生未知錯誤: {e}", exc_info=True)
        return None