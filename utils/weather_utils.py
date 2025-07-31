# utils/weather_utils.py

# --- 新增的蒲福風級描述函數 ---
def get_beaufort_scale_description(wind_scale_int: int) -> str:
    """
    根據蒲福風級數字返回對應的文字描述。
    Args:
        wind_scale_int (int): 蒲福風級數字 (0-12)。
    Returns:
        str: 蒲福風級的文字描述。
    """
    if wind_scale_int == 0:
        return "無風"
    elif wind_scale_int == 1:
        return "軟風"
    elif wind_scale_int == 2:
        return "輕風"
    elif wind_scale_int == 3:
        return "微風"
    elif wind_scale_int == 4:
        return "和風"
    elif wind_scale_int == 5:
        return "清風"
    elif wind_scale_int == 6:
        return "強風"
    elif wind_scale_int == 7:
        return "疾風"
    elif wind_scale_int == 8:
        return "大風"
    elif wind_scale_int == 9:
        return "烈風"
    elif wind_scale_int == 10:
        return "狂風"
    elif wind_scale_int == 11:
        return "暴風"
    elif wind_scale_int == 12:
        return "颶風"
    else:
        return "N/A" # 超出範圍或無效風級

# --- 新增的風速轉換函式 ---
def convert_ms_to_beaufort_scale(wind_speed_ms: float) -> int:
    """
    將風速 (m/s) 轉換為蒲福風級 (Beaufort scale)。
    參考中央氣象署風級對照表 (簡化)。
    """
    if wind_speed_ms < 0.3:
        return 0 # 無風
    elif wind_speed_ms <= 1.5:
        return 1 # 軟風
    elif wind_speed_ms <= 3.3:
        return 2 # 輕風
    elif wind_speed_ms <= 5.4:
        return 3 # 微風
    elif wind_speed_ms <= 7.9:
        return 4 # 和風
    elif wind_speed_ms <= 10.7:
        return 5 # 勁風
    elif wind_speed_ms <= 13.8:
        return 6 # 強風
    elif wind_speed_ms <= 17.1:
        return 7 # 疾風
    elif wind_speed_ms <= 20.7:
        return 8 # 大風
    elif wind_speed_ms <= 24.4:
        return 9 # 烈風
    elif wind_speed_ms <= 28.4:
        return 10 # 狂風
    elif wind_speed_ms <= 32.6:
        return 11 # 暴風
    else:
        return 12 # 颶風 (或更高)