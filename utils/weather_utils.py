# utils/weather_utils.py
"""
天氣數據處理工具庫，用於處理和轉換與天氣相關的原始數據，使其更具可讀性和實用性。
將氣象局 API 返回的原始數值（如風速 m/s）轉換為對用戶更友好的格式（如蒲福風級的文字描述）。
將這些轉換邏輯集中管理，避免在多個地方重複編寫相同的程式碼，並確保數據處理的一致性。
"""
# --- 蒲福風級描述函式 ---
def get_beaufort_scale_description(wind_scale_int: int) -> str:
    """
    將蒲福風級的數字代碼轉換成易於理解的文字描述。
    接收一個 0 到 12 的整數，並返回對應的風級名稱，例如「微風」、「強風」等。

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
        return "無資料" # 超出範圍或無效風級

# --- 風速轉換函式 ---
def convert_ms_to_beaufort_scale(wind_speed_ms: float) -> int:
    """
    將每秒公尺（m/s）為單位的風速，轉換為對應的蒲福風級數字。
    轉換邏輯是基於中央氣象署的風級對照表，每個風級對應一個特定的風速範圍。

    Args:
        wind_speed_ms (float): 風速（m/s）。
    Returns:
        int: 蒲福風級的數字代碼。
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
        return 5 # 清風
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
        return 12 # 颶風