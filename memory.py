import sqlite3

db = sqlite3.connect("sextbot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    persona TEXT,
    paid INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    user_id INTEGER,
    message TEXT,
    is_user INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

def save_user(user_id, username, persona):
    cursor.execute("REPLACE INTO users (user_id, username, persona) VALUES (?, ?, ?)",
                   (user_id, username, persona))
    db.commit()

def get_persona(user_id):
    cursor.execute("SELECT persona FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def save_message(user_id, message, is_user):
    cursor.execute("INSERT INTO chat_history (user_id, message, is_user) VALUES (?, ?, ?)",
                   (user_id, message, is_user))
    db.commit()

def get_last_messages(user_id, limit=10):
    cursor.execute("SELECT message, is_user FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                   (user_id, limit))
    return cursor.fetchall()[::-1]  # return in chronological order

def get_user_message_count(user_id):
    """Get total number of user messages sent"""
    cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND is_user = 1", (user_id,))
    return cursor.fetchone()[0]

def is_user_paid(user_id):
    """Check if user has paid"""
    cursor.execute("SELECT paid FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def mark_user_paid(user_id):
    """Mark user as paid"""
    cursor.execute("UPDATE users SET paid = 1 WHERE user_id = ?", (user_id,))
    db.commit()
