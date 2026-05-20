import os
import sqlite3
import pytest
from app.db_connection import DBConnection

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users (name) VALUES ('Alice'), ('Bob')")
    conn.commit()
    conn.close()
    return str(db_file)

def test_list_tables(temp_db):
    db = DBConnection()
    db.connect(temp_db)
    tables = db.list_tables()
    assert "users" in tables
    db.disconnect()

def test_schema_returns_dict(temp_db):
    db = DBConnection()
    db.connect(temp_db)
    schema = db.get_schema()
    assert isinstance(schema, dict)
    assert "users" in schema
    assert len(schema["users"]) == 2
    assert schema["users"][0]["name"] == "id"
    db.disconnect()
