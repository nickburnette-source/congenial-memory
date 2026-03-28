import sqlite3
import os
from datetime import datetime

DB_PATH = "/app/data/agent_tasks.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            task_text TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS agent_reports (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            agent_id INTEGER,
            role TEXT,
            result TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_task(task_text: str) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (task_text, status, created_at) VALUES (?, 'running', ?)",
              (task_text, datetime.now().isoformat()))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id

def log_agent_report(task_id: int, agent_id: int, role: str, result: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO agent_reports (task_id, agent_id, role, result, timestamp) VALUES (?, ?, ?, ?, ?)",
              (task_id, agent_id, role, result, datetime.now().isoformat()))
    conn.commit()
    conn.close()