# utils/api_helper.py
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, MessagingApiBlob

# 讀取環境變數或你現有的 config
from config import LINE_CHANNEL_ACCESS_TOKEN

# 全局實例，避免重複建立
_conf = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
_api_client = ApiClient(_conf)  # 避免重複建立

# MessagingApi 實例
_messaging_api = MessagingApi(_api_client)

# 新增 MessagingApiBlob 實例
_messaging_api_blob = MessagingApiBlob(_api_client)

def get_line_bot_apis():
    """
    獲取 Line Bot Messaging API 和 Blob API 的實例。
    用於需要同時操作訊息和檔案（如 Rich Menu 圖片）的場景。
    """
    # 直接返回兩個預先創建好的全局實例
    return _messaging_api, _messaging_api_blob

def get_messaging_api():
    """取得共用的 MessagingApi 實例"""
    return _messaging_api