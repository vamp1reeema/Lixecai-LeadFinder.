import sqlite3
from config import DB_PATH

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS source_state (
        source TEXT PRIMARY KEY,
        last_message_id INTEGER NOT NULL DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def get_last_id(conn, source):
    row = conn.execute(
        "SELECT last_message_id FROM source_state WHERE source = ?", (source,)
    ).fetchone()
    return row[0] if row else 0

def set_last_id(conn, source, message_id):
    conn.execute("""INSERT INTO source_state(source, last_message_id)
        VALUES(?, ?) ON CONFLICT(source) DO UPDATE SET
        last_message_id = MAX(last_message_id, excluded.last_message_id)""",
        (source, message_id))
    conn.commit()

def get_flag(conn, key):
    row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None

def set_flag(conn, key, value):
    conn.execute("""INSERT INTO app_state(key, value) VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value""", (key, value))
    conn.commit()
