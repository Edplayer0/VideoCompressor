import sqlite3

DATABASE = "users.db"

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE, check_same_thread=False)

    def _get_user(self, chat_id: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT chat_id, role FROM users WHERE chat_id = ?", (chat_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def verify_id(self, chat_id: str) -> bool:
        return self._get_user(chat_id) is not None

    def verify_admin(self, chat_id: str) -> bool:
        row = self._get_user(chat_id)
        return row is not None and row[1] == "admin"

    def close(self):
        self.conn.close()

db_manager = DatabaseManager()

