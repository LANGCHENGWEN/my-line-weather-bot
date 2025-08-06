# typhoon/typhoon_parser.py
# 這個檔案負責接收 typhoon_api_client.py 獲取到的原始 JSON 數據，並將其解析、整理成更容易在 Flex Message 中使用的格式
import re
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from .typhoon_constants import DIRECTION_MAP

logger = logging.getLogger(__name__)

class TyphoonParser:
    """
    解析中央氣象署颱風 API (W-C0034-005) 的原始 JSON 數據，
    並將其格式化為 Flex Message 友好的結構。
    """
    def _format_radius_detail_cht(self, detail_str: str) -> list[str]:
        """
        內部方法：將英文縮寫的風暴半徑詳細資訊轉換為中文並分段。
        例如: "(NE170公里, SE180公里)" -> ["東北170公里", "東南180公里", ...]
        """
        if not detail_str:
            return [] # 返回空列表
        
        # 這裡加入對 DIRECTION_MAP 的檢查，以防萬一它變成 None
        if DIRECTION_MAP is None:
            logger.error("format_radius_detail_cht 中的 DIRECTION_MAP 為 None。這表示存在導入問題。")
            return [detail_str] # 無法轉換，返回包含原始字串的列表

        parts = re.split(r',\s*', detail_str.strip('() '))

        formatted_parts = []

        # 遍歷 DIRECTION_MAP，先替換較長的詞，確保 "NNE" 不會被 "N" 先替換
        try:
            sorted_directions = sorted(
                [k for k in DIRECTION_MAP.keys() if k is not None],
                key=len,
                reverse=True
            )
        except TypeError as e:
            logger.error(f"Error sorting DIRECTION_MAP keys: {e}. DIRECTION_MAP: {DIRECTION_MAP}")
            return [detail_str] # 無法轉換，返回包含原始字串的列表
    
        for part in parts:
            if not part:
                continue
            # 遍歷排序過的方向，嘗試替換
            replaced = False
            for eng_dir in sorted_directions:
                if eng_dir and part.startswith(eng_dir):
                    remaining_part = part[len(eng_dir):]
                    formatted_parts.append(f"{DIRECTION_MAP[eng_dir]}{remaining_part}")
                    replaced = True
                    break
            if not replaced:  # 如果沒有匹配到任何方向，則保留原樣
                formatted_parts.append(part)

        # 為了讓 Flex Message 更容易處理兩行顯示，確保至少有四個元素，不足則補空字串
        # 這假設了 Flex Message 會嘗試取出 index 0, 1, 2, 3 的元素
        while len(formatted_parts) < 4:
            formatted_parts.append("")
        return formatted_parts

    def parse_typhoon_data(self, raw_typhoon_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        從原始颱風數據中提取並整理出用於顯示的關鍵資訊。
        返回的字典包含 'currentStatus' 和 'forecasts' (列表)。
        'forecasts' 列表中的每個預報點都已包含格式化好的時間等資訊。
        """
        if not raw_typhoon_data:
            logger.warning("無原始颱風數據可供解析。")
            return None

        try:
            # 從最外層 records.tropicalCyclones.tropicalCyclone[0] 開始提取
            tropical_cyclone_data = raw_typhoon_data \
                                    .get("records", {}) \
                                    .get("tropicalCyclones", {}) \
                                    .get("tropicalCyclone", [])
            if not tropical_cyclone_data:
                logger.warning("未找到任何熱帶氣旋數據。")
                return None
            
            # 假設我們只處理第一個颱風 (通常只有一個活躍颱風，或取最新的)
            typhoon_info = tropical_cyclone_data[0]

            # 提取並格式化現況資訊
            current_status = self._parse_current_status(typhoon_info)

            # 提取並格式化預報點資訊 (這會返回一個列表)
            forecasts = self._parse_forecast_data(typhoon_info)

            # 從解析後的數據中獲取預報點，確保按 tau 排序後取指定時效的
            forecast_24hr = next((f for f in forecasts if f.get('tau') == 24), None)
            forecast_48hr = next((f for f in forecasts if f.get('tau') == 48), None)
            forecast_72hr = next((f for f in forecasts if f.get('tau') == 72), None)

            return {
                "currentStatus": current_status,
                "forecasts": forecasts,
                "forecast_24hr": forecast_24hr, # 新增特定時效的預報點
                "forecast_48hr": forecast_48hr,
                "forecast_72hr": forecast_72hr
            }

        except Exception as e:
            logger.error(f"解析颱風數據時發生錯誤: {e}", exc_info=True)
            return None

    def _parse_current_status(self, typhoon_info: Dict[str, Any]) -> Dict[str, Any]:
        """解析颱風現況數據並格式化。"""
        # 從 JSON 資料中提取 year 和 typhoonName
        year = typhoon_info.get("year")
        typhoon_eng_name = typhoon_info.get("typhoonName")

        # 組合年份和英文名，創建一個唯一的颱風 ID
        typhoon_id = f"{year}_{typhoon_eng_name}" if year and typhoon_eng_name else "無資料"

        current_status = {
            "typhoon_id": typhoon_id,
            "typhoonName": typhoon_info.get("cwaTyphoonName", "無資料"), # 中文颱風名
            "typhoonEngName": typhoon_info.get("typhoonName", "無資料"), # 英文颱風名
            "tdNo": typhoon_info.get("cwaTdNo", "無資料"), # 國際編號
            "dataTime": "未知日期", # 觀測時間
            "longitude": "無資料",
            "latitude": "無資料",
            "maxWindSpeed": "無資料",
            "maxGustSpeed": "無資料",
            "pressure": "無資料",
            "movingSpeed": "無資料",
            "movingDirection": "無資料",
            "radiusOf7knots": "無資料",
            "radiusOf7knotsDetailFormatted": ["", "", "", ""] # 預先初始化為列表，確保有四個空字串
        }

        # 取得即時位置和強度資訊 (通常在 analysisData.fix 裡面)
        analysis_data = typhoon_info.get("analysisData", {})
        fix_data_list = analysis_data.get("fix", [])

        # 確保有 fix 資料並且取最新的
        if fix_data_list:
            # 假設 fix_data_list 已經是按時間排序的，取最後一個作為最新實測
            # 取得最新的觀測數據
            latest_fix = fix_data_list[-1]

            # 觀測時間 (fixTime)
            raw_fix_time = latest_fix.get("fixTime")
            if raw_fix_time:
                try:
                    # 將類似 "2025-07-20T14:00:00+08:00" 的字串轉換為可讀格式
                    # 注意: datetime.fromisoformat 在處理時區資訊時可能會根據 Python 版本有不同行為
                    # 最保險的方式是手動處理或使用第三方庫如 dateutil
                    # 這裡假設只需要提取時間部分並格式化
                    dt_object = datetime.fromisoformat(raw_fix_time)
                    # 將時間格式化為 "YYYY-MM-DD HH:MM" 或 "MM/DD HH:MM"
                    current_status["dataTime"] = dt_object.strftime("%Y年%m月%d日 %H:%M") 
                except ValueError:
                    logger.warning(f"解析 fixTime '{raw_fix_time}' 失敗。", exc_info=True)
                    current_status["dataTime"] = "未知日期"

            # 現況細節資訊 - 直接從 latest_fix 提取，因為 JSON 結構是扁平的
            # 座標
            coordinate_str = latest_fix.get("coordinate")
            if coordinate_str and isinstance(coordinate_str, str):
                coords = coordinate_str.split(',')
                if len(coords) == 2:
                    # CWA 座標格式是 "經度,緯度"，所以第一個是經度，第二個是緯度
                    current_status["longitude"] = coords[0].strip()
                    current_status["latitude"] = coords[1].strip()
                else:
                    logger.warning(f"現況座標字串格式不符預期: {coordinate_str}")
            
            current_status["maxWindSpeed"] = latest_fix.get("maxWindSpeed", "無資料")
            current_status["maxGustSpeed"] = latest_fix.get("maxGustSpeed", "無資料")
            current_status["pressure"] = latest_fix.get("pressure", "無資料")

            # 移動方向和速度
            current_status["movingSpeed"] = latest_fix.get("movingSpeed", "無資料")

            # --- 新增的修改：轉換移動方向為中文 ---
            raw_moving_direction = latest_fix.get("movingDirection")
            if raw_moving_direction and raw_moving_direction in DIRECTION_MAP:
                current_status["movingDirection"] = DIRECTION_MAP[raw_moving_direction]
            else:
                current_status["movingDirection"] = raw_moving_direction if raw_moving_direction else "無資料"
            
            # 七級風暴風半徑
            radius_7knots_data = latest_fix.get("circleOf15Ms", {})
            current_status["radiusOf7knots"] = radius_7knots_data.get("radius", "無資料") # 七級風暴風半徑 (總範圍)
            
            # 處理暴風半徑詳細方向 (例如 東北100km, 西南80km)
            # 假設 current_detail.circleOf15Ms.radiusOfDirection 存在且為列表
            quadrant_radii_7knots = radius_7knots_data.get("quadrantRadii", {}).get("radius")
            
            detail_str_for_formatting = ""
            if isinstance(quadrant_radii_7knots, list):
                # 預期格式如 [{"direction": "NE", "radius": "120"}, {"direction": "SW", "radius": "80"}]
                # 這裡只取前兩個方向的半徑作為範例
                dir_info = []
                for r_dir in quadrant_radii_7knots:
                    if isinstance(r_dir, dict):
                        direction = r_dir.get('dir') # 鍵名是 'dir'
                        value = r_dir.get('value') # 鍵名是 'value'
                        if direction and value is not None: # 確保有值
                            dir_info.append(f"{direction}{value}公里")
                detail_str_for_formatting = f"({', '.join(dir_info)})" if dir_info else ""

            # 呼叫格式化函式，將結果儲存到 radiusOf7knotsDetailFormatted
            current_status["radiusOf7knotsDetailFormatted"] = self._format_radius_detail_cht(detail_str_for_formatting)

        else:
            logger.warning("未找到任何颱風實測 (fix) 數據，現況資訊將為 無資料。")
            # 如果沒資料，設定為空字串列表，而不是單一空字串
            current_status["radiusOf7knotsDetailFormatted"] = ["", "", "", ""]
        
        return current_status

    def _parse_forecast_data(self, typhoon_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        # 提取預報點資訊
        forecast_data_list = typhoon_info.get("forecastData", {}).get("fix", [])
        parsed_forecasts = []

        for forecast_point in forecast_data_list:
            tau_hours = forecast_point.get("tau")
            # 確保 tau_hours 是有效的數字字串
            if not tau_hours or not tau_hours.isdigit() or int(tau_hours) == 0:
                logger.debug(f"跳過無效或為0的預報時效 (tau): {tau_hours}") # <-- 使用 logger.debug
                continue

            tau_hours_int = int(tau_hours)

            # 計算預報時間
            # CWA 的 dataTime 是 UTC+8，tau 是小時數
            raw_init_time = forecast_point.get("initTime")
            forecast_time_formatted = "無資料"

            if raw_init_time:
                try:
                    init_dt_object = datetime.fromisoformat(raw_init_time)
                    # 計算預報時間 (initTime + tau 小時)
                    calculated_forecast_time = init_dt_object + timedelta(hours=tau_hours_int)
                    # 格式化為 MM/DD HH:MM
                    forecast_time_formatted = calculated_forecast_time.strftime("%m/%d %H:%M")
                except ValueError:
                    logger.warning(f"解析 initTime '{raw_init_time}' 或計算預報時間失敗。", exc_info=True)

            # 處理經緯度格式
            coordinate_str_forecast = forecast_point.get("coordinate")
            longitude_forecast = "無資料"
            latitude_forecast = "無資料"
            
            if coordinate_str_forecast and isinstance(coordinate_str_forecast, str):
                coords_forecast = coordinate_str_forecast.split(',')
                if len(coords_forecast) == 2:
                    longitude_forecast = coords_forecast[0].strip() # 經度在第一個
                    latitude_forecast = coords_forecast[1].strip() # 緯度在第二個
                else:
                    logger.warning(f"預報點座標格式不符預期: {coordinate_str_forecast}")

            # 預報風速、氣壓
            max_wind_speed_forecast = forecast_point.get("maxWindSpeed", "無資料")
            max_gust_speed_forecast = forecast_point.get("maxGustSpeed", "無資料")
            pressure_forecast = forecast_point.get("pressure", "無資料")

            # 七級風暴風半徑 (預報點)
            radius_7knots_forecast_data = forecast_point.get("circleOf15Ms", {})
            radius_7knots_forecast = radius_7knots_forecast_data.get("radius", "無資料")

            # 70% 機率半徑 (預報點)
            # 您提供的 JSON 中，radiusOf70PercentProbability 是一個直接的鍵，值是字串
            radius_70_percent_prob_forecast = forecast_point.get("radiusOf70PercentProbability", "無資料")

            parsed_forecasts.append({
                "tau": tau_hours_int,
                "forecastTime": forecast_time_formatted,
                "longitude": longitude_forecast,
                "latitude": latitude_forecast,
                "maxWindSpeed": max_wind_speed_forecast,
                "maxGustSpeed": max_gust_speed_forecast,
                "pressure": pressure_forecast,
                "radiusOf7knots": radius_7knots_forecast,
                "radiusOf70PercentProbability": radius_70_percent_prob_forecast
            })
            
        # 將預報點按 tau 排序
        # 使用 "0" 作為預設值，避免非數字錯誤
        parsed_forecasts.sort(key=lambda x: x["tau"])

        """
        return {
            "currentStatus": current_status,
            "forecasts": parsed_forecasts
        }
        """
        return parsed_forecasts

"""
# 範例使用 (取消註解可進行測試)
if __name__ == "__main__":
    # 模擬從 CWA API 獲取到的原始 JSON 數據
    # 這應該是從 typhoon_api_client.py 的 fetch_typhoon_raw_data() 返回的數據
    sample_raw_data = {
        "dataTime": "2025-07-18 20:00:00",
        "cwaTyphoonName": "薇帕",
        "typhoonName": "WIPHA",
        "cwaTdNo": "09",
        "current": {
            "coordinate": {"latitude": "19.2", "longitude": "121.8"},
            "maxWindSpeed": "20",
            "maxGustSpeed": "28",
            "pressure": "990",
            "movingSpeed": "34",
            "movingDirection": "WNW",
            "circleOf15Ms": {"radius": "100", "radiusOfDirection": [{"direction": "NE", "radius": "120"}, {"direction": "SW", "radius": "80"}]}
        },
        "forecastData": {
            "fix": [
                {"tau": "6", "coordinate": "120.5,19.8", "maxWindSpeed": "23", "maxGustSpeed": "30", "pressure": "988", "circleOf15Ms": {"radius": "120"}, "radiusOf70PercentProbability": "30"},
                {"tau": "24", "coordinate": "117.4,21.1", "maxWindSpeed": "30", "maxGustSpeed": "38", "pressure": "975", "circleOf15Ms": {"radius": "200"}, "circleOf25Ms": {"radius": "70"}, "radiusOf70PercentProbability": "90"},
                {"tau": "48", "coordinate": "111.8,21.9", "maxWindSpeed": "30", "maxGustSpeed": "38", "pressure": "975", "circleOf15Ms": {"radius": "220"}, "circleOf25Ms": {"radius": "70"}, "radiusOf70PercentProbability": "170"},
                {"tau": "72", "coordinate": "108.0,21.1", "maxWindSpeed": "25", "maxGustSpeed": "33", "pressure": "985", "circleOf15Ms": {"radius": "180"}, "radiusOf70PercentProbability": "210"}
            ]
        }
    }

    parser = TyphoonParser()
    parsed_data = parser.parse_typhoon_data(sample_raw_data)

    if parsed_data:
        print("\n--- 解析後的颱風數據 ---")
        print("現況:", parsed_data["currentStatus"])
        print("\n預報點:")
        for fcst in parsed_data["forecasts"]:
            print(f"  tau {fcst['tau']}h ({fcst['forecastTime']}): 位置({fcst['latitude']},{fcst['longitude']}), 風速{fcst['maxWindSpeed']}/{fcst['maxGustSpeed']}, 氣壓{fcst['pressure']}")
    else:
        print("解析颱風數據失敗。")
"""