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
            columns = []
            for row in cursor.fetchall():
                col = {
                    "name": row["name"],
                    "type": row["type"] or "TEXT",
                    "pk": bool(row["pk"]),
                    "notnull": bool(row["notnull"]),
                    "default": row["dflt_value"],
                }
                columns.append(col)

            # Gather unique columns via index introspection
            unique_cols = set()
            try:
                idx_cursor = self.conn.cursor()
                idx_cursor.execute(f"PRAGMA index_list('{table}')")
                for idx_row in idx_cursor.fetchall():
                    if idx_row["unique"]:
                        info_cursor = self.conn.cursor()
                        info_cursor.execute(f"PRAGMA index_info('{idx_row['name']}')")
                        idx_cols = info_cursor.fetchall()
                        if len(idx_cols) == 1:
                            unique_cols.add(idx_cols[0]["name"])
            except Exception:
                pass

            for col in columns:
                col["unique"] = col["name"] in unique_cols

            schema[table] = columns
        return schema

    def get_sample_rows(self, table: str, limit: int = 3) -> dict:
        """Return {'columns': [...], 'rows': [[...], ...]} for sample data."""
        if not self.conn:
            return {"columns": [], "rows": []}
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM \"{table}\" LIMIT {limit}")
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [list(row) for row in cursor.fetchall()]
            return {"columns": columns, "rows": rows}
        except Exception:
            return {"columns": [], "rows": []}

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
                    SELECT column_name, data_type,
                           is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row["column_name"],
                        "type": row["data_type"].upper(),
                        "pk": False,
                        "notnull": row["is_nullable"] == "NO",
                        "default": row["column_default"],
                        "unique": False,
                    })

                # Find primary key columns
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'
                """, (table,))
                pk_cols = {row["column_name"] for row in cursor.fetchall()}

                # Find unique columns
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s AND tc.constraint_type = 'UNIQUE'
                """, (table,))
                unique_cols = {row["column_name"] for row in cursor.fetchall()}

                for col in columns:
                    col["pk"] = col["name"] in pk_cols
                    col["unique"] = col["name"] in unique_cols

                schema[table] = columns
        return schema

    def get_sample_rows(self, table: str, limit: int = 3) -> dict:
        """Return {'columns': [...], 'rows': [[...], ...]} for sample data."""
        if not self.conn:
            return {"columns": [], "rows": []}
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(f'SELECT * FROM "{table}" LIMIT {limit}')
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [list(row) for row in cursor.fetchall()]
                return {"columns": columns, "rows": rows}
        except Exception:
            return {"columns": [], "rows": []}

def get_db_connection(config: dict):
    db_type = config.get("type")
    if db_type == "postgres":
        return PostgresConnection()
    return SQLiteConnection()
