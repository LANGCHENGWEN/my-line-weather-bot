# weather_today/cwa_today_api.py
import logging
import requests
from config import CWA_FORECAST_36HR_API
from utils.text_processing import normalize_city_name
# from utils.major_stations import COUNTY_TO_STATION_MAP, ALL_TAIWAN_COUNTIES

logger = logging.getLogger(__name__)

def get_cwa_today_data(api_key: str, location_name: str) -> dict | None:
    """
    從中央氣象署 F-C0032-001 取得指定縣市的今明36小時天氣預報資料。

    Args:
        api_key (str): 中央氣象署開放資料平台 API 金鑰。
        location_name (str): 欲查詢的縣市名稱 (例如: "臺中市")。

    Returns:
        dict | None: 成功時返回 JSON 格式的原始天氣資料，失敗時返回 None。
    """
    url = CWA_FORECAST_36HR_API

    # 在進行映射前，先將用戶輸入的 location_name 進行標準化
    query_location_name = normalize_city_name(location_name)
    logger.debug(f"標準化後的 location_name: '{query_location_name}'")

    params = {
        "Authorization": api_key,
        "format": "JSON",
        "locationName": [query_location_name],
        "elementName": ["Wx, PoP, MinT, MaxT, CI"] # 取得天氣現象, 降雨機率, 最低溫, 最高溫, 舒適度
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}") # 新增日誌

    try:
        logger.info(f"正在從中央氣象署 API ({CWA_FORECAST_36HR_API}) 取得 {location_name} 的今日天氣資料..")
        response = requests.get(url, params=params)
        response.raise_for_status()  # 如果狀態碼不是 200，則拋出 HTTPError

        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")

        data = response.json()
        # 確保這一行存在，並且它的日誌級別是 DEBUG
        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 這裡可以再加一個檢查：如果 data['records']['location'] 是空的，也視為資料取得失敗
        if not data.get("records", {}).get("location"):
            logger.warning(f"從中央氣象署 API 成功取得回應，但 {location_name} 的 'location' 數據為空。")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"從中央氣象署 API 取得即時觀測資料時發生連線超時錯誤。")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"從中央氣象署 API 取得即時觀測資料時發生 HTTP 錯誤: {e.response.status_code} - {e.response.text}", exc_info=True)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"從中央氣象署 API 取得即時觀測資料時發生網路錯誤: {e}", exc_info=True)
        return None
    except ValueError as e:
        logger.error(f"解析中央氣象署即時觀測 API 回應時發生 JSON 解析錯誤: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"取得中央氣象署即時觀測資料時發生未知錯誤: {e}", exc_info=True)
        return None