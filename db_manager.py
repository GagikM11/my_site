import sqlite3
import os

# Путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def init_db():
    """Создает базу данных и таблицу при первом запуске"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT,
            message TEXT,
            time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_message(nickname, message, time_str):
    """Сохраняет новое сообщение"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (nickname, message, time) VALUES (?, ?, ?)',
                       (nickname, message, time_str))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return False

def fetch_all_messages():
    """Получает все сообщения из базы"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, message, time FROM messages ORDER BY id ASC')
        rows = cursor.fetchall()
        conn.close()
        
        # Преобразуем кортежи в список словарей
        return [{"nickname": r[0], "message": r[1], "time": r[2]} for r in rows]
    except Exception as e:
        print(f"Ошибка чтения БД: {e}")
        return []
