import requests
import sqlite3
import re
from .db_connection import get_db_connection

class DestructiveQueryError(Exception):
    def __init__(self, message, sql=""):
        super().__init__(message)
        self.sql = sql

def handle_nl_query(nl_text: str, db_config: dict, ollama_url: str = 'http://localhost:11434') -> dict:
    """
    1. Fetch schema from db_config
    2. Build prompt and call Ollama
    3. Check for destructive keywords -> raise DestructiveQueryError
    4. Execute SQL against DB
    5. Return { sql, columns, rows, affected, error }
    """
    db = get_db_connection(db_config)
    db.connect(db_config)
    schema = db.get_schema()
    
    # Format schema context
    schema_context = ""
    for table, cols in schema.items():
        schema_context += f"Table: {table}\nColumns: "
        schema_context += ", ".join([f"{col['name']} ({col['type']})" for col in cols])
        schema_context += "\n\n"
        
    db_type = "PostgreSQL" if db_config.get("type") == "postgres" else "SQLite"
    prompt = f"""### Task
Generate a SQL query for {db_type} that answers the question.
Return ONLY the SQL. No explanation. No markdown.

### Database Schema
{schema_context}

### Question
{nl_text}

### SQL
"""

    response = requests.post(f"{ollama_url}/api/generate", json={
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False
    })
    
    if response.status_code != 200:
        return {
            "sql": "", "columns": [], "rows": [], "affected": 0, 
            "error": f"Ollama API error: {response.text}"
        }
        
    sql = response.json().get("response", "").strip()
    
    # Strip markdown code blocks if Ollama included them
    sql = re.sub(r"^```sql\n", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\n", "", sql)
    sql = re.sub(r"\n```$", "", sql)
    sql = sql.strip()
    
    # Destructive keyword check
    destructive_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE"]
    upper_sql = sql.upper()
    for kw in destructive_keywords:
        if re.search(rf"\b{kw}\b", upper_sql):
            db.disconnect()
            raise DestructiveQueryError(f"Destructive operation detected: {kw}", sql=sql)
            
    # Execute SQL
    try:
        cursor = db.conn.cursor()
        cursor.execute(sql)
        if sql.upper().startswith("SELECT"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            affected = 0
            # Convert rows from sqlite3.Row to list of tuples or dicts
            rows_data = [list(row) for row in rows]
            db.disconnect()
            return {"sql": sql, "columns": columns, "rows": rows_data, "affected": affected, "error": None}
        else:
            db.conn.commit()
            affected = cursor.rowcount
            db.disconnect()
            return {"sql": sql, "columns": [], "rows": [], "affected": affected, "error": None}
    except Exception as e:
        db.disconnect()
        return {"sql": sql, "columns": [], "rows": [], "affected": 0, "error": str(e)}

def explain_sql(sql: str, nl_text: str, ollama_url: str = 'http://localhost:11434') -> str:
    prompt = f"""### Task
Explain in simple, plain English what the following SQL query does in relation to the user's question.
Keep the explanation to one short paragraph.

### User Question
{nl_text}

### SQL Query
{sql}

### Explanation
"""

    try:
        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False
        })
        
        if response.status_code != 200:
            return f"Error fetching explanation: {response.text}"
            
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error fetching explanation: {str(e)}"

def analyze_database(nl_text: str, db_config: dict, ollama_url: str = 'http://localhost:11434') -> str:
    db = get_db_connection(db_config)
    db.connect(db_config)
    
    try:
        schema = db.get_schema()
        
        # Format schema context
        schema_context = ""
        for table, cols in schema.items():
            schema_context += f"Table: {table}\nColumns: "
            schema_context += ", ".join([f"{col['name']} ({col['type']})" for col in cols])
            schema_context += "\n\n"
            
        prompt = f"""### Task
Analyze the following database schema based on the user's question.
Provide a clear, concise, and helpful explanation in plain English.
Do NOT generate SQL queries.

### Database Schema
{schema_context}

### User Question
{nl_text}

### Analysis
"""

        response = requests.post(f"{ollama_url}/api/generate", json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False
        })
        
        if response.status_code != 200:
            return f"Error fetching analysis: {response.text}"
            
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error analyzing database: {str(e)}"
    finally:
        db.disconnect()
