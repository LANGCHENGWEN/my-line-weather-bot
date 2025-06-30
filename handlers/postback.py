# handlers/postback.py
# from weather_forecast.postback_handler import handle_forecast_postback
from menu_handlers.settings_menu_handler import handle_settings_menu_postback
from utils.api_helper import get_messaging_api
'''
def handle(event):
    line_bot_api = get_messaging_api()
    if handle_forecast_postback(line_bot_api, event):
        return
    if handle_settings_menu_postback(line_bot_api, event):
        return
    # 其他 postback…
'''