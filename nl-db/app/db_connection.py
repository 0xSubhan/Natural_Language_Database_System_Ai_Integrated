import sqlite3
import psycopg2
import psycopg2.extras

class SQLiteConnection:
    def __init__(self):
        self.conn = None
        self.config = None

    def connect(self, config: dict):
        self.disconnect()
        self.config = config
        path = config.get("path")
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.config = None

    def list_tables(self) -> list[str]:
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return [row[0] for row in cursor.fetchall()]

    def get_schema(self) -> dict:
        if not self.conn:
            return {}
        schema = {}
        for table in self.list_tables():
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table}')")
            schema[table] = [{"name": row["name"], "type": row["type"]} for row in cursor.fetchall()]
        return schema

class PostgresConnection:
    def __init__(self):
        self.conn = None
        self.config = None

    def connect(self, config: dict):
        self.disconnect()
        self.config = config
        self.conn = psycopg2.connect(
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            user=config.get("user", ""),
            password=config.get("password", ""),
            dbname=config.get("dbname", "")
        )
        self.conn.cursor_factory = psycopg2.extras.DictCursor

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.config = None

    def list_tables(self) -> list[str]:
        if not self.conn:
            return []
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            return [row['table_name'] for row in cursor.fetchall()]

    def get_schema(self) -> dict:
        if not self.conn:
            return {}
        schema = {}
        with self.conn.cursor() as cursor:
            for table in self.list_tables():
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                """, (table,))
                schema[table] = [{"name": row["column_name"], "type": row["data_type"]} for row in cursor.fetchall()]
        return schema

def get_db_connection(config: dict):
    db_type = config.get("type")
    if db_type == "postgres":
        return PostgresConnection()
    return SQLiteConnection()
