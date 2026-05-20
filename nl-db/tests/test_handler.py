import pytest
import sqlite3
from unittest.mock import patch
from app.query_handler import handle_nl_query, DestructiveQueryError

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

@patch('app.query_handler.requests.post')
def test_select_returns_rows(mock_post, temp_db):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"response": "SELECT * FROM users;"}
            
    mock_post.return_value = MockResponse()
    
    result = handle_nl_query("Get all users", temp_db)
    
    assert result["error"] is None
    assert "sql" in result
    assert result["sql"] == "SELECT * FROM users;"
    assert len(result["rows"]) == 2
    assert "Alice" in result["rows"][0]
    assert "Bob" in result["rows"][1]

@patch('app.query_handler.requests.post')
def test_destructive_raises(mock_post, temp_db):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"response": "DROP TABLE users;"}
            
    mock_post.return_value = MockResponse()
    
    with pytest.raises(DestructiveQueryError) as excinfo:
        handle_nl_query("Delete all users table", temp_db)
        
    assert "DROP" in str(excinfo.value).upper()
    assert excinfo.value.sql == "DROP TABLE users;"
