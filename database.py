import sqlite3
from typing import Optional

class SQLiteDB:
    def init(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        # Создаем таблицу пользователей, если её еще нет
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
            return row[0] if row else None

# Создаем один глобальный объект базы данных
db = SQLiteDB()
