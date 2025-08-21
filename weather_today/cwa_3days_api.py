# weather_today/cwa_3days_api.py
import logging
import requests
from config import CWA_FORECAST_3DAYS_API
from utils.text_processing import normalize_city_name

logger = logging.getLogger(__name__)

def get_cwa_3days_data(api_key: str, location_name: str) -> dict | None:
    """
    獲取指定地點的未來天氣預報數據。
    :param dataset_id: 資料集 ID，預設為 F-D0047-089。
    :param location_name: 要查詢的地點名稱，預設為臺中市。
    :return: 包含天氣數據的字典，如果請求失敗則返回 None。
    """
    url = CWA_FORECAST_3DAYS_API

    # 在進行映射前，先將用戶輸入的 location_name 進行標準化
    query_location_name = normalize_city_name(location_name)
    logger.debug(f"標準化後的 location_name: '{query_location_name}'")

    params = {
        "Authorization": api_key,
        "format": "JSON",
        "locationName": [query_location_name],
        # 我們只關心特定的天氣元素，可以通過 fields 參數篩選
        "fields": "LocationName,WeatherElement",
        "elementName": ["相對濕度", "風向", "風速", "體感溫度"] # 篩選需要的元素
    }
    logger.debug(f"向中央氣象署 API 發送請求的參數: {params}") # 新增日誌

    try:
        logger.info(f"正在從中央氣象署 API ({CWA_FORECAST_3DAYS_API}) 取得 {location_name} 的今日天氣資料..")
        # 發送 HTTP GET 請求
        # `timeout=10` 設置超時時間，防止程式因網路延遲而卡住
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # # 這是 `requests` 函式庫的一個功能；如果 HTTP 響應狀態碼不是 2xx，會自動拋出一個 `HTTPError`

        logger.debug(f"中央氣象署 API 原始回應文字 (當 elementName 啟用時):\n{response.text}")

        data = response.json() # 把一個 HTTP 回應（response）物件的內容，解析成 Python 的字典或列表等資料結構
        # 確保這一行存在，並且它的日誌級別是 DEBUG
        logger.debug(f"接收到的 CWA API 原始資料: {data}")

        # 新增檢查 'success' 字段
        # 驗證 API 回應的成功狀態
        if data.get("success") != "true":
            logger.warning(f"CWA API 回應 'success' 為 False，未能成功取得資料。回應內容: {data.get('message', '無訊息')}")
            return None
        
        locations_data = data.get("records", {}).get("Locations", [])
        if locations_data:
            logger.info(f"成功取得 {location_name} 的今日天氣資料。")
            return data
        else:
            # API 請求成功但數據內容不符合預期
            logger.warning(f"從中央氣象署 API 成功取得回應，但未找到 'Locations' 數據。")
            return None # 數據無效，返回 None

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

# # 範例用法 (在實際應用中，API 金鑰應從環境變數或安全配置中讀取)
# if __name__ == "__main__":
#     # 替換為您的實際 API 金鑰
#     # 建議從環境變數獲取: os.environ.get("CWB_API_KEY")
#     api_key = "YOUR_CWB_API_KEY"
#     if api_key == "YOUR_CWB_API_KEY":
#         print("請將 YOUR_CWB_API_KEY 替換為您的中央氣象局 API 金鑰。")
#     else:
#         client = WeatherAPIClient(api_key)
#         data = client.get_forecast_data(location_name="臺中市")
#         if data:
#             print("成功獲取天氣數據！")
#             # 可以將數據保存下來或傳遞給解析器
#             # import json
#             # with open("raw_weather_data.json", "w", encoding="utf-8") as f:
#             #     json.dump(data, f, ensure_ascii=False, indent=2)
#         else:
#             print("獲取天氣數據失敗。")