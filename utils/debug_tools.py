# utils/debug_tools.py

import json
import logging

logger = logging.getLogger(__name__)

def debug_parsed_weather(parsed_weather: dict, raw_api_data: dict = None):
    logger.debug("=== Debug Parsed Weather Start ===")

    if raw_api_data:
        logger.debug("原始API資料：\n%s", json.dumps(raw_api_data, indent=2, ensure_ascii=False))
    else:
        logger.debug("沒有提供原始API資料。")

    if not parsed_weather:
        logger.warning("解析後的資料是空的。")
        logger.debug("=== Debug Parsed Weather End ===")
        return

    location_name = parsed_weather.get("location_name", "無地區名稱")
    county_name = parsed_weather.get("county_name", "無縣市")
    num_periods = len(parsed_weather.get("forecast_periods", []))

    logger.debug("解析結果: 地區: %s, 縣市: %s", location_name, county_name)
    logger.debug("預報時段數量: %d", num_periods)

    for i, period in enumerate(parsed_weather.get("forecast_periods", [])[:10]):
        logger.debug(
            "時段 %d: 日期: %s, 時間: %s, 天氣: %s, 最高溫: %s, 最低溫: %s, 降雨機率: %s",
            i+1,
            period.get("forecast_date", "N/A"),
            period.get("obs_time", "N/A"),
            period.get("weather_desc", "N/A"),
            period.get("max_temp", "N/A"),
            period.get("min_temp", "N/A"),
            period.get("pop", "N/A"),
        )

    logger.debug("=== Debug Parsed Weather End ===")