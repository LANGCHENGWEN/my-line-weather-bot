# typhoon/typhoon_constants.py
# 存放與颱風相關的靜態常數和對應表
# 將中央氣象署 API 中使用的颱風路徑方向英文縮寫，與中文名稱進行對應
DIRECTION_MAP = {
    "N"      : "北",
    "NNE"    : "東北",
    "NE"     : "東北",
    "ENE"    : "東北東",
    "E"      : "東",
    "ESE"    : "東南東",
    "SE"     : "東南",
    "SSE"    : "南南東",
    "S"      : "南",
    "SSW"    : "南南西",
    "SW"     : "西南",
    "WSW"    : "西南西",
    "W"      : "西",
    "WNW"    : "西北西",
    "NW"     : "西北",
    "NNW"    : "北北西",
    "Varies" : "不規則",
    "NoData" : "不明",
    None     : "不明"
}