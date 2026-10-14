import sqlite3
from typing import Optional

class SQLiteDB:
    def __init__(self):
        self.db_path = "users.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_class TEXT NOT NULL
                )
            """)
            conn.commit()

    async def set_user_class(self, user_id: int, user_class: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, user_class) VALUES (?, ?)",
                (user_id, user_class.strip().upper())
            )
            conn.commit()

    async def get_user_class(self, user_id: int) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_class FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return row[0] # Исправлено: возвращаем чистую строку класса
            return None

db = SQLiteDB()
