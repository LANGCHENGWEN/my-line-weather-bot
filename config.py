# config.py
# 這個檔案將負責配置你的 API 金鑰和 logging 系統
import os # 引入 os 模組，用於操作作業系統環境變數
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv # 從 dotenv 模組引入 load_dotenv 函數，用於加載 .env 檔案中的環境變數

load_dotenv() # 加載 .env 檔案中的環境變數到 os.environ，這樣就可以透過 os.getenv() 取得

ENABLE_DAILY_NOTIFICATIONS = False # 設置為 False 即可暫停

# --- Line Bot 設定 ---
# 這是 LINE Bot 用來發送訊息到 LINE 平台的憑證
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
# 這是 LINE Bot 用來驗證 LINE 平台發送的 Webhook 請求是否合法的密鑰
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

IS_DEBUG_MODE = True                # 本機開發請設 True，上線請改 False
ENABLE_DAILY_NOTIFICATIONS = False  # 先關閉；上線想推播再改 True

# --- 交通部中央氣象署 Open Data 平台 API 設定 --- # 
CWA_API_KEY = os.getenv('CWA_API_KEY')
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/" # API 基本網址 (共同前綴)
LOCATION_NAME = "臺中市"
DEFAULT_COUNTY = "臺中市"  # 查詢資料的城市名稱

YOUR_LINE_USER_ID = os.getenv("YOUR_LINE_USER_ID")

# --- 各功能對應的 CWA API 端點 ---
# 1. 即時天氣查詢 (Current Weather Observations)
# 資料集名稱：自動氣象站-氣象觀測資料 (Automated Weather Station - Meteorological Observation Data)
# 提供氣溫、濕度、風速等即時資料。
CWA_CURRENT_WEATHER_API = CWA_BASE_URL + "O-A0003-001" # O-A0001-001(1小時更新)

# 2. 未來天氣預報 (Future Weather Forecasts)
# 2.1 鄉鎮天氣預報-臺灣未來3天天氣預報 (包含未來36小時詳細預報)
# 提供天氣現象、降雨機率、最高/最低溫度、風速等。
CWA_FORECAST_36HR_API = CWA_BASE_URL + "F-C0032-001" # ***F‑C0032‑001(適合找城市) # ***F-D0047-089(適合找城市+區域) # F-C0032-005

# 2.2 鄉鎮天氣預報-臺灣未來1週天氣預報 (包含未來7天預報)
# 提供天氣現象、最高/最低溫度等，降雨機率通常只到前三天。
CWA_FORECAST_1WEEK_API = CWA_BASE_URL + "F-D0047-091" # ***F-D0047-091 # F-D0047-093

# 3. 颱風資訊 (Typhoon Information)
# 3.1 颱風消息與警報-颱風警報
# 提供目前颱風名稱、位置、移動、風速、半徑等基本資訊。
CWA_TYPHOON_WARNING_API = CWA_BASE_URL + "W-C0034-005"

# 3.2 颱風消息與警報-颱風侵襲機率
# 提供各地區受颱風侵襲的機率。
CWA_TYPHOON_PROBABILITY_API = CWA_BASE_URL + "W-C0033-002"

# 4. 天氣特報 (Weather Alerts/Warnings)
# 資料集名稱：天氣特報-各別縣市地區目前之天氣警特報情形
# 提供豪大雨、強風、低溫等警特報資訊。
CWA_WEATHER_ALERTS_API = CWA_BASE_URL + "W-C0033-001"

# --- 颱風路徑圖連結 (非API，直接提供官方網頁連結) ---
# 您可以引導使用者前往此網址查看最新颱風路徑圖。
CWA_TYPHOON_MAP_URL = "https://app.cwa.gov.tw/web/obsmap/typhoon.html"

# --- Logging 配置 ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")


# --- Logging Configuration ---
def setup_logging(name='root', level=logging.DEBUG): # 預設日誌器名稱為 'root'，等級為 DEBUG
    """
    設定全局的 logging 配置。
    日誌會輸出到文件並在午夜輪換。
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # 避免重複添加 handler，導致日誌重複輸出
    # 這是統一設置日誌系統的關鍵步驟
    logger = logging.getLogger(name)
    if not logger.handlers: # 只有在沒有 handler 的時候才添加
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 檔案日誌，每天午夜輪換，保留7份備份
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level) # 可以根據需要設定檔案日誌的等級

        # 控制台日誌
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level) # 可以根據需要設定控制台日誌的等級

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logger.setLevel(level) # 設定日誌器的整體等級
    logger.propagate = False # 避免日誌傳遞給父級日誌器，防止重複輸出

    return logger

main_logger = setup_logging(name='root', level=logging.DEBUG) # 設置 'root' logger
main_logger.debug("Logging 系統已設定完成。")