# cwa_forecast_api.py
# 專門處理天氣預報的 API 呼叫
import logging
import requests
from config import CWA_FORECAST_1WEEK_API

logger = logging.getLogger(__name__)

def get_cwa_forecast_data(api_key: str, location_name: str) -> dict:
    """
    從中央氣象署 API 取得臺灣各縣市鄉鎮未來一週天氣預報資料 (F-D0047-091)。
    Args:
        api_key (str): 中央氣象署 API 授權碼。
        township_name (str): 鄉鎮市區名稱 (e.g., "北區")。此 API 直接以鄉鎮市區為單位提供數據。
    Returns:
        dict: 取得的天氣資料原始 JSON 字典，如果失敗則返回空字典。
    """
    url = CWA_FORECAST_1WEEK_API
    params = {
        "Authorization": api_key,
        "locationName": location_name,
        # F-D0047-091 常用的氣象元素 (請根據實際資料集文件確認)
        # 這些是鄉鎮一週預報常見的元素，包含白天/晚上時段
        "elementName": "Wx,MaxT,MinT,PoP6h,T,RH,CI,WS,Wd", # 天氣現象、最高溫、最低溫、6小時降雨機率、溫度、相對濕度、舒適度指數、風速、風向
        # 注意：T 通常代表平均溫度，MinT/MaxT 代表日最高/最低。PoP6h 為 6 小時降雨機率。
        # 具體要取哪個，取決於您希望在訊息中展示的方式。這裡我把可能用到的都列出來。
        "format": "JSON"
    }
    try:
        logger.info(f"正在從中央氣象署 API 取得 {location_name} 的天氣預報資料...")
        response = requests.get(url, params=params)
        # 增加日誌來打印 HTTP 狀態碼
        logger.debug(f"CWA API response status code: {response.status_code}")
        # 增加日誌來打印原始響應文本 (非常重要，用於診斷 Expecting value 錯誤)
        logger.debug(f"CWA API raw response text: {response.text}")
        
        response.raise_for_status()
        data = response.json()
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