import sqlite3

def get_conn():
    return sqlite3.connect(
        "threads.db",
        check_same_thread=False
    )

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            chat_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def create_thread(thread_id: str, chat_name: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO threads (thread_id, chat_name) VALUES (?, ?)",
        (str(thread_id), chat_name)
    )
    conn.commit()
    conn.close()

def get_threads():
    conn = get_conn()
    rows = conn.execute("""
        SELECT thread_id, chat_name
        FROM threads
        ORDER BY created_at ASC
    """).fetchall()
    conn.close()
    return rows

