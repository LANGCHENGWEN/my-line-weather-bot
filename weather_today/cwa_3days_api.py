# weather_today/cwa_3days_api.py
"""
與中央氣象署的「未來 3 天縣市天氣預報」API 進行溝通。
主要職責：
1. 根據用戶指定的縣市名稱，向中央氣象署 API 發送 HTTP 請求。
2. 處理 API 回應，包括成功獲取資料、連線超時、HTTP 錯誤等各種情況。
3. 將成功的 JSON 回應轉換成 Python 字典並返回，供後續程式碼進行解析和使用。
4. 在發送請求前後，以及在處理回應的各個階段，記錄詳細的日誌，以便於偵錯和追蹤。
"""
import logging
import requests
from config import CWA_FORECAST_3DAYS_API
from utils.text_processing import normalize_city_name

logger = logging.getLogger(__name__)

def get_cwa_3days_data(api_key: str, location_name: str) -> dict | None:
    """
    獲取指定地點的未來 3 天天氣預報數據。
    向中央氣象署的指定 API 發送請求，並處理所有可能的連線和資料錯誤。
    進行參數的正規化，並在每個關鍵步驟記錄日誌，確保操作的透明性和可追溯性。
    """
    # --- 設置 API URL ---
    url = CWA_FORECAST_3DAYS_API

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
        "fields"        : "LocationName,WeatherElement",
        "elementName"   : ["相對濕度", "風向", "風速", "體感溫度"] # 篩選需要的元素
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}")

    # --- 發送請求與錯誤處理 ---
    try:
        logger.info(f"正在從中央氣象署 API ({CWA_FORECAST_3DAYS_API}) 取得 {location_name} 的今日天氣資料..")
        # 使用 `requests` 函式庫發送 HTTP GET 請求
        # `timeout=10` 設置超時時間，防止程式因網路延遲而卡住
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`

        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")

        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構
        
        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 驗證 API 回應的成功狀態
        if data.get("success") != "true":
            logger.warning(f"CWA API 回應 'success' 為 False，未能成功取得資料。回應內容: {data.get('message', '無訊息')}")
            return None
        
        # 驗證 'records' 結構
        locations_data = data.get("records", {}).get("Locations", [])
        if locations_data:
            logger.info(f"成功取得 {location_name} 的今日天氣資料。")
            return data
        else:
            # API 請求成功但數據內容不符合預期
            logger.warning(f"從中央氣象署 API 成功取得回應，但未找到 'Locations' 數據。")
            return None

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