# user_data_manager.py
import sqlite3
from pathlib import Path
from config import setup_logging
logger = setup_logging(__name__)

# 建立資料庫檔案與資料表
DB_PATH = Path("user_data.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    default_city TEXT,
    state TEXT
)
""")
conn.commit()

# ---- 狀態管理 ----
def set_user_state(user_id: str, state: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, state)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=excluded.state
        """, (user_id, state))
        conn.commit()

def get_user_state(user_id: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def clear_user_state(user_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET state = NULL WHERE user_id = ?
        """, (user_id,))
        conn.commit()

# ---- 預設城市管理 ----
def save_default_city(user_id: str, city_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, default_city)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET default_city=excluded.default_city
        """, (user_id, city_name))
        conn.commit()

def get_default_city(user_id: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT default_city FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

# ---- 驗證城市名稱 ----
def is_valid_city(city_name: str) -> bool:
    # 可改成讀取實際縣市資料庫或 API 驗證
    valid_cities = ["台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市"]
    return city_name in valid_cities