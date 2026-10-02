import sqlite3

DATABASE = "users.db"

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)

    def verify_id(self, chat_id: str) -> bool:

        cursor = self.conn.cursor()

        cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()

        cursor.close()

        if result:
            return True

    def verify_admin(self, chat_id: str) -> bool:

        cursor = self.conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()

        cursor.close()

        if (result[0] == "admin"):
            return True

db_manager = DatabaseManager()
