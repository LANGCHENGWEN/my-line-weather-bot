# typhoon/typhoon_parser.py
# 這個檔案負責接收 typhoon_api_client.py 獲取到的原始 JSON 數據，並將其解析、整理成更容易在 Flex Message 中使用的格式
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class TyphoonParser:
    """
    解析中央氣象署颱風 API (W-C0034-005) 的原始 JSON 數據。
    """

    def parse_typhoon_data(self, raw_typhoon_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        從原始颱風數據中提取並整理出用於顯示的關鍵資訊。
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

            # 提取現況資訊
            current_status = {
                "typhoonName": typhoon_info.get("cwaTyphoonName", "N/A"), # 中文颱風名
                "typhoonEngName": typhoon_info.get("typhoonName", "N/A"), # 英文颱風名
                "tdNo": typhoon_info.get("cwaTdNo", "N/A"), # 國際編號
                "dataTime": "N/A", # 觀測時間
                "longitude": "N/A",
                "latitude": "N/A",
                "maxWindSpeed": "N/A",
                "maxGustSpeed": "N/A",
                "pressure": "N/A",
                "movingSpeed": "N/A",
                "movingDirection": "N/A",
                "radiusOf7knots": "N/A",
                "radiusOf7knotsDetail": ""
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
                        current_status["dataTime"] = "N/A"

                # 現況細節資訊 - 直接從 latest_fix 提取，因為 JSON 結構是扁平的
                coordinate_str = latest_fix.get("coordinate")
                if coordinate_str and isinstance(coordinate_str, str):
                    coords = coordinate_str.split(',')
                    if len(coords) == 2:
                        # CWA 座標格式是 "經度,緯度"，所以第一個是經度，第二個是緯度
                        current_status["longitude"] = coords[0].strip()
                        current_status["latitude"] = coords[1].strip()
                    else:
                        logger.warning(f"現況座標字串格式不符預期: {coordinate_str}")
                
                current_status["maxWindSpeed"] = latest_fix.get("maxWindSpeed", "N/A")
                current_status["maxGustSpeed"] = latest_fix.get("maxGustSpeed", "N/A")
                current_status["pressure"] = latest_fix.get("pressure", "N/A")
                current_status["movingSpeed"] = latest_fix.get("movingSpeed", "N/A")
                current_status["movingDirection"] = latest_fix.get("movingDirection", "N/A")
                
                # 七級風暴風半徑
                radius_7knots_data = latest_fix.get("circleOf15Ms", {})
                current_status["radiusOf7knots"] = radius_7knots_data.get("radius", "N/A") # 七級風暴風半徑 (總範圍)
                
                # 處理暴風半徑詳細方向 (例如 東北100km, 西南80km)
                # 假設 current_detail.circleOf15Ms.radiusOfDirection 存在且為列表
                quadrant_radii_7knots = radius_7knots_data.get("quadrantRadii", {}).get("radius")
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
                    current_status["radiusOf7knotsDetail"] = f"({', '.join(dir_info)})" if dir_info else ""
                else:
                    current_status["radiusOf7knotsDetail"] = "" # 如果沒資料，設定為空字串

            else:
                logger.warning("未找到任何颱風實測 (fix) 數據，現況資訊將為 N/A。")

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
                forecast_time_formatted = "N/A"

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
                longitude_forecast = "N/A"
                latitude_forecast = "N/A"
                
                if coordinate_str_forecast and isinstance(coordinate_str_forecast, str):
                    coords_forecast = coordinate_str_forecast.split(',')
                    if len(coords_forecast) == 2:
                        longitude_forecast = coords_forecast[0].strip() # 經度在第一個
                        latitude_forecast = coords_forecast[1].strip() # 緯度在第二個
                    else:
                        logger.warning(f"預報點座標格式不符預期: {coordinate_str_forecast}")

                # 預報風速、氣壓
                max_wind_speed_forecast = forecast_point.get("maxWindSpeed", "N/A")
                max_gust_speed_forecast = forecast_point.get("maxGustSpeed", "N/A")
                pressure_forecast = forecast_point.get("pressure", "N/A")

                # 七級風暴風半徑 (預報點)
                radius_7knots_forecast_data = forecast_point.get("circleOf15Ms", {})
                radius_7knots_forecast = radius_7knots_forecast_data.get("radius", "N/A")

                # 70% 機率半徑 (預報點)
                # 您提供的 JSON 中，radiusOf70PercentProbability 是一個直接的鍵，值是字串
                radius_70_percent_prob_forecast = forecast_point.get("radiusOf70PercentProbability", "N/A")

                parsed_forecasts.append({
                    "tau": tau_hours,
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
            parsed_forecasts.sort(key=lambda x: int(x.get("tau", 0)))

            return {
                "currentStatus": current_status,
                "forecasts": parsed_forecasts
            }

        except Exception as e:
            logger.error(f"解析颱風數據時發生錯誤: {e}", exc_info=True)
            return None

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