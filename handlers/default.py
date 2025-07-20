# default.py
# 處理未識別的訊息
# 傳送未識別訊息的回覆：透過 send_unrecognized_message 函數，向使用者回覆一條訊息，通常是用來告知使用者「你的訊息無法辨識」或提供一些可用的指令/關鍵字
from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_unrecognized_message

def handle(event):
    line_bot_api = get_messaging_api()
    send_unrecognized_message(line_bot_api, event)