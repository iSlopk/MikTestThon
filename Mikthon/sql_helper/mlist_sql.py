import sqlite3

conn = sqlite3.connect("mlist.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS mlist_attendance (
    chat_id INTEGER,
    reply_to INTEGER,
    user_id INTEGER,
    PRIMARY KEY (chat_id, reply_to, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mlist_logs (
    chat_id INTEGER PRIMARY KEY,
    log_chat_id INTEGER,
    topic_id INTEGER
)
""")

conn.commit()

def add_user(chat_id, reply_to, user_id):
    cursor.execute("INSERT OR IGNORE INTO mlist_attendance (chat_id, reply_to, user_id) VALUES (?, ?, ?)",
                   (chat_id, reply_to, user_id))
    conn.commit()

def remove_user(chat_id, reply_to, user_id):
    cursor.execute("DELETE FROM mlist_attendance WHERE chat_id=? AND reply_to=? AND user_id=?",
                   (chat_id, reply_to, user_id))
    conn.commit()

def get_users(chat_id, reply_to):
    cursor.execute("SELECT user_id FROM mlist_attendance WHERE chat_id=? AND reply_to=?",
                   (chat_id, reply_to))
    return [row[0] for row in cursor.fetchall()]

def set_log_channel(chat_id, log_chat_id, topic_id):
    cursor.execute("REPLACE INTO mlist_logs (chat_id, log_chat_id, topic_id) VALUES (?, ?, ?)",
                   (chat_id, log_chat_id, topic_id))
    conn.commit()

def get_log_channel(chat_id):
    cursor.execute("SELECT log_chat_id, topic_id FROM mlist_logs WHERE chat_id=?", (chat_id,))
    row = cursor.fetchone()
    return tuple(row) if row else None