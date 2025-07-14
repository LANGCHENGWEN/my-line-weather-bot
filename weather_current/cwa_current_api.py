# cwa_current_api.py
# 專門處理即時天氣的 API 呼叫 (O-A0003-001 有人氣象站資料)
import logging
import requests
from config import CWA_CURRENT_WEATHER_API
from .major_stations import COUNTY_TO_STATION_MAP, ALL_TAIWAN_COUNTIES, normalize_location_name

logger = logging.getLogger(__name__)

def get_cwa_current_data(api_key: str, location_name: str) -> dict | None:
    """
    從中央氣象署 API 取得即時觀測資料。
    請將 '您的即時觀測資料的 CWA API URL' 替換為實際的 API URL，
    並根據該 API 的參數調整 'params'。
    常見的即時觀測 API 如 O-A0001-001、O-A0003-001。
    location_name 應為用戶輸入的縣市名稱 (例如: 臺中市)。
    函數會將縣市名稱轉換為對應的主要測站名稱進行查詢。
    """
    # 範例 URL (請替換為您要使用的即時觀測 API URL)
    url = CWA_CURRENT_WEATHER_API

    # 在進行映射前，先將用戶輸入的 location_name 進行標準化
    normalized_location_name = normalize_location_name(location_name)
    logger.debug(f"標準化後的 location_name: '{normalized_location_name}'")

    logger.debug(f"進入 get_cwa_current_data，收到的 location_name: '{location_name}'")

    # 檢查 location_name 是否在我們的映射表中
    # 如果 location_name 是縣市名稱，則從映射中獲取對應的測站名稱
    # 否則，假設 location_name 已經是一個測站名稱 (例如用戶直接輸入了"臺北")
    station_to_query = COUNTY_TO_STATION_MAP.get(normalized_location_name, normalized_location_name)

    # 這裡也加入 DEBUG 日誌，查看映射後的測站名稱
    logger.debug(f"經過映射後，要查詢的測站名稱 station_to_query: '{station_to_query}'")

    # 如果經過映射後，仍無法找到對應的測站 (例如用戶輸入了非縣市/非測站名稱)
    # 或者原始輸入的縣市根本不在我們的預期列表中，可以返回 None 或拋出錯誤
    # 這裡可以增加一個額外的檢查，確保如果原始輸入是縣市名稱，則必須找到對應的測站
    if location_name in ALL_TAIWAN_COUNTIES and station_to_query == normalized_location_name:
        # 排除那些用戶輸入就是測站名而不在映射表裡的正常情況
        # 這裡的邏輯可以更精細，例如檢查 normalized_location_name 是否在 ALL_TAIWAN_COUNTIES 裡
        # 並且它沒有被成功映射到不同的測站名
        if normalized_location_name in ALL_TAIWAN_COUNTIES and \
           COUNTY_TO_STATION_MAP.get(normalized_location_name) is None:
            logger.warning(f"無法將縣市 '{location_name}' (標準化為 '{normalized_location_name}') 映射到已知的主要測站。請檢查 major_stations.py。")
            return None
        '''
        logger.warning(f"無法將縣市 '{location_name}' 映射到已知的主要測站。請檢查 major_stations.py。")
        return None
    elif location_name not in ALL_TAIWAN_COUNTIES and station_to_query == location_name:
        # 如果用戶輸入的不是預設縣市，且它也不是我們映射後的測站名，
        # 這裡可以選擇性地進一步處理，例如：假設它就是一個測站名稱直接查詢，
        # 或者提示用戶輸入無效。為了避免錯誤，這裡暫時讓它嘗試查詢。
        pass
        '''

    params = {
        "Authorization": api_key,
        "format": "JSON",
        "limit": 1, # 只取最新一筆資料
        "StationName": [station_to_query], # 如果API可以用測站名稱篩選
        "elementName": ["Weather", "AirTemperature", "RelativeHumidity", "Precipitation", "WindSpeed", "WindDirection", "AirPressure", "UVIndex"] # <-- 明確要求這些天氣元素
        # "CountyName": location_name, # 如果API可以用縣市名稱篩選
        # 對於 O-A0001-001，可能需要篩選 'LocationName' 或 'StationName'，或獲取所有再程式碼中過濾
        # ... 其他可能參數，例如 'dataid' 等 ...
        # WeatherElement
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}") # 新增日誌

    try:
        logger.info(f"正在從中央氣象署 API ({CWA_CURRENT_WEATHER_API}) 取得 {location_name} 的即時觀測資料...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # 檢查 HTTP 錯誤 (2xx 表示成功，否則拋出異常)

        # --- 在這裡加入偵錯日誌，印出原始回應文字 ---
        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")
        # --- 繼續您的邏輯 ---

        data = response.json()

        # 確保這一行存在，並且它的日誌級別是 DEBUG
        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 再次檢查 API 響應的 'success' 狀態和 'records' 結構
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
    
"""
# --- 測試程式碼 ---
if __name__ == "__main__":
    # 在這裡假設 config.CWA_API_KEY 已經被正確設定
    # 如果還沒設定，你需要手動在這裡填入你的金鑰，或者在運行前設置環境變數
    
    # 設置一個你希望查詢的城市名稱
    test_city = "臺中市" # 使用 CWA API 上的正式名稱「臺中市」
    
    logger.debug(f"\n--- 開始測試 get_cwa_current_data 函數 ---")
    logger.debug(f"正在嘗試查詢城市: {test_city}")
    
    # 呼叫函數
    weather_data = get_cwa_current_data(CWA_API_KEY, test_city)
    
    if weather_data:
        logger.debug(f"\n成功獲取到 {test_city} 的天氣資料！")
        logger.debug("資料概覽 (只顯示前兩個地點的名稱):")
        for i, loc in enumerate(weather_data):
            if i >= 2: # 只顯示前面幾個地點避免輸出過長
                break
            logger.debug(f"  地點 {i+1}: {loc.get('locationName')}")
            # 如果想看更多細節，可以 uncomment 下面這行
            # import json
            # logger.debug(json.dumps(loc, indent=2, ensure_ascii=False)) 
        logger.debug(f"\n共獲取到 {len(weather_data)} 個地點的資料。")
    else:
        logger.debug(f"\n無法獲取 {test_city} 的天氣資料。請檢查：")
        logger.debug("1. 你的 CWA_API_KEY 是否正確且有效。")
        logger.debug("2. 你在 config.py 中 `CWA_CURRENT_WEATHER_API` 的 URL 是否正確。")
        logger.debug("3. 網路連接是否正常。")
        logger.debug("4. `location_name` (例如 '臺中市') 是否符合 CWA API 的要求。")

    logger.debug(f"\n--- 測試結束 ---")
"""