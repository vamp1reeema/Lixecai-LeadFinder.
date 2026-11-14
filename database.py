import sqlite3
from config import DB_PATH

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_state (
        chat_id INTEGER PRIMARY KEY,
        last_message_id INTEGER NOT NULL DEFAULT 0
    )""")
    conn.commit()
    return conn

def get_last_id(conn, chat_id):
    row = conn.execute(
        "SELECT last_message_id FROM chat_state WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row[0] if row else 0

def set_last_id(conn, chat_id, message_id):
    conn.execute("""INSERT INTO chat_state(chat_id, last_message_id)
        VALUES(?, ?) ON CONFLICT(chat_id) DO UPDATE SET
        last_message_id = MAX(last_message_id, excluded.last_message_id)""",
        (chat_id, message_id))
    conn.commit()
