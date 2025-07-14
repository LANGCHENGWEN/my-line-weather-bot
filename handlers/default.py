from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_unrecognized_message

def handle(event):
    line_bot_api = get_messaging_api()
    send_unrecognized_message(line_bot_api, event)