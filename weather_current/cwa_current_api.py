# weather_current/cwa_current_api.py
"""
處理中央氣象署（CWA）即時觀測資料的 API 呼叫 (O-A0003-001 有人氣象站資料)。
主要職責：
1. 數據獲取：使用 `requests` 函式庫向指定的 CWA API 端點發送 HTTP 請求，獲取即時天氣數據。
2. 參數準備：將用戶輸入的城市名稱（如「臺北市」）轉換為 API 所需的測站名稱（如「臺北」）。
3. 錯誤處理：處理各種可能的網路和 API 響應錯誤，例如連線超時、HTTP 錯誤或無效的 JSON 格式，確保程式的穩定性。
4. 日誌記錄：在整個請求和響應過程中記錄詳細的日誌，便於開發和除錯。
"""
import logging
import requests
from config import CWA_CURRENT_WEATHER_API
from utils.text_processing import normalize_city_name
from utils.major_stations import COUNTY_TO_STATION_MAP, ALL_TAIWAN_COUNTIES

logger = logging.getLogger(__name__)

def get_cwa_current_data(api_key: str, location_name: str) -> dict | None:
    """
    從中央氣象署 API 取得指定地點的即時觀測資料。
    接收一個 API Key 和一個城市名稱，然後將城市名稱轉換為對應的測站名稱進行 API 查詢。
    如果請求成功並獲得有效數據，會返回一個字典；如果發生任何錯誤，則返回 None。
    """
    # 1. 設置 API URL
    url = CWA_CURRENT_WEATHER_API

    # 2. 處理地點名稱
    # 在進行映射前，先將用戶輸入的 location_name 進行標準化
    normalized_location_name = normalize_city_name(location_name)
    logger.debug(f"標準化後的 location_name: '{normalized_location_name}'")

    logger.debug(f"進入 get_cwa_current_data，收到的 location_name: '{location_name}'")

    """
    這段程式碼處理兩種可能的輸入情況：
    1. 用戶輸入縣市名稱：例如「臺中市」，程式會在 `COUNTY_TO_STATION_MAP` 中查找對應的測站名稱（如「臺中」）。
    2. 用戶輸入測站名稱：例如「臺北」，如果輸入不在映射表中，程式會直接使用這個輸入作為查詢測站。
    這種邏輯增加函式的彈性，可以處理更多樣的用戶輸入。
    """
    station_to_query = COUNTY_TO_STATION_MAP.get(normalized_location_name, normalized_location_name)
    logger.debug(f"經過映射後，要查詢的測站名稱 station_to_query: '{station_to_query}'")

    """
    映射失敗時提供更精確的錯誤處理和日誌記錄。
    用戶輸入一個在 ALL_TAIWAN_COUNTIES 列表中的有效縣市名稱（例如 "新北市"）。
    但由於 major_stations.py 中的 COUNTY_TO_STATION_MAP 字典沒有為這個縣市定義對應的氣象站，導致 station_to_query 變數與原始的 normalized_location_name 相同。
    """
    if location_name in ALL_TAIWAN_COUNTIES and station_to_query == normalized_location_name:
        if normalized_location_name in ALL_TAIWAN_COUNTIES and \
           COUNTY_TO_STATION_MAP.get(normalized_location_name) is None:
            logger.warning(f"無法將縣市 '{location_name}' (標準化為 '{normalized_location_name}') 映射到已知的主要測站。請檢查 major_stations.py。")
            return None

    # 3. 準備 API 請求參數
    params = {
        "Authorization": api_key,          # 自己的 API Key，用於身份驗證
        "format": "JSON",                  # 指定返回資料的格式，這裡使用 JSON
        "limit": 1,                        # 限制返回的記錄數量，`1` 表示只獲取最新的資料，提高效率
        "StationName": [station_to_query], # 使用映射後得到的測站名稱來精確查詢，而不是獲取所有數據
        "elementName": ["Weather", "AirTemperature", "RelativeHumidity", "Precipitation", "WindSpeed", "WindDirection", "AirPressure", "UVIndex"] # 明確指定需要哪些天氣元素，減少不必要的數據傳輸量
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}")

    # 4. 發送請求與錯誤處理
    try:
        logger.info(f"正在從中央氣象署 API ({CWA_CURRENT_WEATHER_API}) 取得 {location_name} 的即時觀測資料...")
        # 發送 HTTP GET 請求
        # `timeout=10` 設置超時時間，防止程式因網路延遲而卡住
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`

        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")

        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構

        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 驗證 API 回應的成功狀態和 'records' 結構
        if data.get('success') == 'true' and data.get('records', {}).get('Station'):
            logger.info(f"成功取得 {location_name} 的即時觀測資料。")
            return data
        else:
            # API 請求成功但數據內容不符合預期
            logger.warning(f"取得 {location_name} 的即時觀測資料成功，但數據為空或格式不符。回應: {data}")
            return None # 數據無效，返回 None
        
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