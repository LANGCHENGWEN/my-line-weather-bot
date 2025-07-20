# rich_menu_configs.py
# 所有 Rich Menu 設定的中央配置中心
# Rich Menu 別名定義
# 這些別名是您的程式碼中用來識別不同 Rich Menu 的字串 ID
# 定義 Rich Menu 的名稱，所有 Rich Menu 別名常數的中央儲存庫
MAIN_MENU_ALIAS = "main_menu_alias"
WEATHER_QUERY_ALIAS = "weather_query_alias"
TYPHOON_ZONE_ALIAS = "typhoon_zone_alias"
LIFE_REMINDER_ALIAS = "life_reminder_alias"
SETTINGS_ALIAS = "settings_alias"

# LINE Bot 的富媒體菜單別名與 ID 映射
# 這些 ID 需要你預先在 LINE Developers Console 或透過 API 上傳富媒體菜單後獲取
RICH_MENU_ALIAS_MAP = {
    "main_menu_alias": "richmenu-8d2c295204caff1289fee7d421c10397", # 請替換為你的主菜單ID
    "weather_query_alias": "richmenu-c4923c799f3bf211c57b091b56b7064d",
    "typhoon_zone_alias": "richmenu-481b92eb23081bb6ca9bc5d49bb8d434",
    "life_reminder_alias": "richmenu-8a17578a9c3ee9af0e579795ee0bd402",
    "settings_menu_alias": "richmenu-7fd1fc84a4a253c645f1790d538b04cb" # 請替換為你的設定菜單ID
    # ... 其他菜單別名
}

# 預設綁定給新加入用戶的富媒體菜單別名
DEFAULT_RICH_MENU_ALIAS = "main_menu_alias" # 或其他你希望新用戶看到的菜單

# 定義所有 Rich Menu 的詳細配置
# 每個字典代表一個 Rich Menu，包含其 JSON 檔案路徑、圖片路徑和對應的別名
ALL_RICH_MENU_CONFIGS = [
    {
        'json_path': 'rich_menu_manager/rich_menus/main_menu.json',
        'image_path': 'rich_menu_manager/rich_menus/main_menu_image.png',
        'alias': MAIN_MENU_ALIAS
    },
    {
        'json_path': 'rich_menu_manager/rich_menus/weather_query_menu.json',
        'image_path': 'rich_menu_manager/rich_menus/weather_query_menu_image.png', # weather_query_menu_image.png
        'alias': WEATHER_QUERY_ALIAS
    },
    {
        'json_path': 'rich_menu_manager/rich_menus/typhoon_zone_menu.json',
        'image_path': 'rich_menu_manager/rich_menus/typhoon_zone_menu_image.png', # typhoon_zone_menu_image.png
        'alias': TYPHOON_ZONE_ALIAS
    },
    {
        'json_path': 'rich_menu_manager/rich_menus/life_reminder_menu.json',
        'image_path': 'rich_menu_manager/rich_menus/life_reminder_menu_image.png', # life_reminder_menu_image.png
        'alias': LIFE_REMINDER_ALIAS
    },
    {
        'json_path': 'rich_menu_manager/rich_menus/settings_menu.json',
        'image_path': 'rich_menu_manager/rich_menus/settings_menu_image.png', # settings_menu_image.png
        'alias': SETTINGS_ALIAS
    }
]

# 除錯模式的設定也可以放在這裡，或者由 app.py 根據環境變數控制
# IS_DEBUG_MODE = True