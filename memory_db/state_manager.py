import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "project_state.db")

class StateManager:
    """
    Manages SQLite database to store project metadata, current configurations, 
    and the action history for pending/approved actions.
    """
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT,
                    target_track TEXT,
                    parameters JSON,
                    status TEXT
                )
            ''')
            conn.commit()

    def log_action(self, action_type: str, target_track: str, parameters: dict, status: str = "pending"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO action_history (action_type, target_track, parameters, status)
                VALUES (?, ?, ?, ?)
            ''', (action_type, target_track, json.dumps(parameters), status))
            conn.commit()
            return cursor.lastrowid

    def update_action_status(self, action_id: int, status: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE action_history SET status = ? WHERE id = ?
            ''', (status, action_id))
            conn.commit()

    def get_pending_actions(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, action_type, target_track, parameters FROM action_history WHERE status = 'pending'
            ''')
            rows = cursor.fetchall()
            return [{"id": row[0], "action_type": row[1], "target_track": row[2], "parameters": json.loads(row[3])} for row in rows]
