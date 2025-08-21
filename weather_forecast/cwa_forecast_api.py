# weather_forecast/cwa_forecast_api.py
"""
與中央氣象署（CWA）的天氣預報 API (F-D0047-091) 進行互動。
建構 API 請求，包括設定授權碼、查詢地點和所需的氣象元素，並處理網路請求的發送和響應的接收。
包含錯誤處理機制，確保在網路連線失敗或 API 回應異常時，程式能夠穩健的運行，並提供日誌訊息。
"""
import logging
import requests
from config import CWA_FORECAST_1WEEK_API

logger = logging.getLogger(__name__)

def get_cwa_forecast_data(api_key: str, location_name: str) -> dict:
    """
    從中央氣象署 API 取得臺灣各縣市未來一週天氣預報資料 (F-D0047-091)。
    這個函式會發送 HTTP GET 請求到指定的 API 端點，並帶上授權碼、查詢地點等參數。
    處理可能發生的網路錯誤或 JSON 解析錯誤，成功時回傳原始的 JSON 數據字典，失敗則回傳空字典。
    """
    url = CWA_FORECAST_1WEEK_API
    params = {
        "Authorization": api_key,
        "locationName": location_name,
        "elementName": "Wx,MaxT,MinT,PoP6h,T,RH,CI,WS,Wd", # 天氣現象、最高溫、最低溫、6 小時降雨機率、平均溫度、相對濕度、舒適度指數、風速、風向
        "format": "JSON"
    }

    # API 請求和錯誤處理
    """
    使用 `requests` 函式庫來發送 GET 請求。
    程式使用 `try...except` 區塊來捕獲可能發生的各種錯誤。
    """
    try:
        logger.info(f"正在從中央氣象署 API 取得 {location_name} 的天氣預報資料...")
        # 發送 HTTP GET 請求
        response = requests.get(url, params=params)
        # 打印 HTTP 狀態碼
        logger.debug(f"CWA API response status code: {response.status_code}")
        # 打印原始響應文本
        logger.debug(f"CWA API raw response text: {response.text}")
        
        response.raise_for_status() # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`
        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構
        logger.info(f"成功取得 {location_name} 的天氣預報資料。")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"從中央氣象署 API 取得預報資料時發生網路錯誤: {e}")
        return {}
    except ValueError as e:
        logger.error(f"解析中央氣象署預報 API 回應時發生錯誤 (無效的 JSON): {e}")
        return {}
    except Exception as e:
        logger.error(f"取得中央氣象署預報資料時發生未知錯誤: {e}")
        return {}