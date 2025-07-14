# user_data_manager.py
import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 建立資料庫檔案與資料表
DB_PATH = Path("user_data.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    default_city TEXT,
    state TEXT,
    meta_json TEXT
)
""")
conn.commit()

# ---------- 工具 ----------
def _get(conn: sqlite3.Connection, col: str, user_id: str):
    cur = conn.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None

def _upsert_cols(user_id: str, **cols):
    keys, vals = zip(*cols.items())
    sets = ", ".join(f"{k}=excluded.{k}" for k in keys)
    placeholders = ", ".join(["?"] * len(keys))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO users (user_id,{','.join(keys)})
            VALUES (?,{placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {sets}
            """,
            (user_id, *vals),
        )
        conn.commit()

# ---- 狀態管理 ----
def set_user_state(user_id: str, state: Optional[str]) -> None:
    logger.debug(f"Executing set_user_state: user_id={user_id}, state={state}")
    with sqlite3.connect(DB_PATH) as conn:
        _upsert_cols(user_id, state=state)
    logger.debug(f"After set_user_state, retrieved state: {get_user_state(user_id)}")

def get_user_state(user_id: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        return _get(conn, "state", user_id)

def clear_user_state(user_id: str) -> None:
    _upsert_cols(user_id, state=None, meta_json=None)

# ---- 預設城市管理 ----
def save_default_city(user_id: str, city_name: str) -> None:
    _upsert_cols(user_id, default_city=city_name)

def get_default_city(user_id: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        return _get(conn, "default_city", user_id)
    
# ---------- 任意 metadata ----------
def set_user_metadata(user_id: str, **kwargs) -> None:
    """
    set_user_metadata("Ua...", weather_type="current", foo="bar")
    會把 meta_json 轉成 dict 後 merge，再寫回。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
        meta: Dict[str, Any] = json.loads(cur_json) if cur_json else {}
        meta.update(kwargs)

    _upsert_cols(user_id, meta_json=json.dumps(meta, ensure_ascii=False))

def get_user_metadata(user_id: str, key: str, default=None):
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
    if not cur_json:
        return default
    try:
        return json.loads(cur_json).get(key, default)
    except json.JSONDecodeError:
        logger.warning("meta_json 解析失敗，已重置")
        _upsert_cols(user_id, meta_json=None)
        return default

# ---- 驗證城市名稱 ----
def is_valid_city(city_name: str) -> bool:
    # 可改成讀取實際縣市資料庫或 API 驗證
    valid_cities = ["台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市"]
    return city_name in valid_cities