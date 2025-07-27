# weather_today/today_uvindex_handler.py
import logging

# 從您的設定檔中導入 API 金鑰
# from config import CWA_API_KEY

from .today_uvindex_api import get_today_uvindex_data
from .today_uvindex_parser import parse_uv_index

logger = logging.getLogger(__name__)

def get_uv_index_for_location(api_key: str, station_id: str) -> dict | None:
    """
    獲取指定測站的每日紫外線指數。

    :param api_key: 您的中央氣象局開放資料平台授權碼。
    :param station_id: 目標測站的 ID (例如: '46749' 代表台中氣象站)。
    :return: 包含紫外線指數的字典 (例如: {"Date": "2025-07-03", "UVIndex": 9})，
             如果獲取失敗或找不到則返回 None。
    """
    logger.info(f"嘗試獲取測站 ID '{station_id}' 的每日紫外線指數。")
    # 直接呼叫 _api.py 中的函式，並傳入 api_key
    raw_uv_data = get_today_uvindex_data(api_key) 

    if not raw_uv_data:
        logger.error("未能從 CWB API 獲取原始紫外線數據。")
        return None

    # 直接呼叫 _parser.py 中的函式
    parsed_uv_data = parse_uv_index(raw_uv_data, station_id)

    if not parsed_uv_data:
        logger.error(f"未能解析測站 ID '{station_id}' 的紫外線數據。")
        return None
    
    logger.info(f"成功獲取並解析測站 ID '{station_id}' 的紫外線數據。")
    return parsed_uv_data

"""
# 範例使用方式 (在您的主程式中調用，假設 API_KEY 已定義)
if __name__ == "__main__":
    # 請替換為您自己的中央氣象局 API 金鑰
    YOUR_CWB_API_KEY = "YOUR_API_KEY" # <<<<<<<<<<<<<<< 請務必替換為您的 API 金鑰

    # 由於您位於北屯區，台中市，建議使用台中氣象站的 StationID (467490) 作為參考
    # 您可能需要查詢中央氣象局網站以獲取最接近北屯區的測站ID
    TAICHUNG_STATION_ID = "467490" 

    # 配置 logging (可選，用於顯示日誌訊息)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    try:
        # 直接呼叫函式，並傳入 API Key
        uv_data = get_uv_index_for_location(YOUR_CWB_API_KEY, TAICHUNG_STATION_ID)

        if uv_data:
            print(f"\n--- 成功獲取紫外線指數 ---")
            print(f"報告日期: {uv_data.get('Date')}")
            print(f"測站 ID: {uv_data.get('StationID')}")
            print(f"紫外線指數: {uv_data.get('UVIndex')}")
            
            # 根據紫外線指數提供建議
            uv_index_val = uv_data.get('UVIndex')
            if uv_index_val is not None:
                if uv_index_val <= 2:
                    print("紫外線指數：低量級，可放心外出。")
                elif 3 <= uv_index_val <= 5:
                    print("紫外線指數：中量級，建議戴太陽眼鏡。")
                elif 6 <= uv_index_val <= 7:
                    print("紫外線指數：高量級，建議戴太陽眼鏡、塗防曬乳。")
                elif 8 <= uv_index_val <= 10:
                    print("紫外線指數：過量級，建議上午10時至下午2時避免外出，並加強防曬。")
                else: # uv_index_val >= 11
                    print("紫外線指數：危險級，建議盡量避免外出，並採取所有防曬措施。")
            
        else:
            print("\n未能獲取紫外線指數資訊。")
    except ValueError as e:
        print(f"錯誤: {e}")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
"""