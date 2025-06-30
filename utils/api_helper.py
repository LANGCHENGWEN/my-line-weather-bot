# utils/api_helper.py
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration

# 讀取環境變數或你現有的 config
from config import LINE_CHANNEL_ACCESS_TOKEN

conf = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

def get_api():
    """
    用 `with get_api() as api:` 取得 MessagingApi 實例
    """
    return ApiClient(conf)

def get_messaging_api():
    """新的：直接回傳 MessagingApi 方便 handler 使用"""
    return MessagingApi(ApiClient(conf))