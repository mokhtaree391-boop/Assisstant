import sqlite3
import threading
import time
from datetime import datetime, timedelta
import os

DB_PATH = "C:/AI_Assistant/memory.db"

def init_task_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            task_type TEXT DEFAULT 'prompt',
            prompt TEXT NOT NULL,
            schedule_type TEXT NOT NULL, -- 'once', 'daily', 'weekly', 'interval'
            run_at TEXT, -- ISO format for 'once'
            repeat_interval INTEGER, -- minutes for 'interval'
            enabled INTEGER DEFAULT 1,
            status TEXT DEFAULT 'idle',
            last_run TEXT,
            next_run TEXT,
            last_result TEXT,
            last_error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            executed_at TEXT,
            status TEXT,
            result TEXT,
            error TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    conn.commit()
    conn.close()

class TaskScheduler:
    def __init__(self, agent_runner_callback):
        self.agent_runner = agent_runner_callback
        self.running = False
        self.thread = None
        init_task_db()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run_loop(self):
        while self.running:
            try:
                self._check_and_execute()
            except Exception as e:
                print(f"Task Scheduler Error: {e}")
            time.sleep(30) # بررسی هر 30 ثانیه

    def _check_and_execute(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("SELECT * FROM tasks WHERE enabled = 1 AND (next_run <= ? OR next_run IS NULL)", (now_str,))
        tasks = cursor.fetchall()

        for task in tasks:
            self._execute_task(task["id"])

        conn.close()

    def _execute_task(self, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            conn.close()
            return

        print(f"Executing task: {task['title']}")
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        status = "success"
        result_text = ""
        error_text = ""

        try:
            if self.agent_runner:
                result_text = self.agent_runner(task["prompt"])
            else:
                result_text = "Agent runner not configured."
        except Exception as e:
            status = "failed"
            error_text = str(e)

        # محاسبه زمان اجرای بعدی
        next_run = self._calculate_next_run(task)
        enabled_status = task["enabled"]
        if task["schedule_type"] == "once":
            enabled_status = 0 # غیرفعال شدن پس از یکبار اجرا

        cursor.execute('''
            UPDATE tasks 
            SET status = ?, last_run = ?, next_run = ?, last_result = ?, last_error = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, start_time, next_run, result_text, error_text, enabled_status, task_id))

        cursor.execute('''
            INSERT INTO task_history (task_id, executed_at, status, result, error)
            VALUES (?, ?, ?, ?, ?)
        ''', (task_id, start_time, status, result_text, error_text))

        conn.commit()
        conn.close()

    def _calculate_next_run(self, task):
        now = datetime.now()
        stype = task["schedule_type"]
        
        if stype == "once":
            return None
        elif stype == "daily":
            return (now + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif stype == "weekly":
            return (now + timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif stype == "interval":
            mins = task["repeat_interval"] or 60
            return (now + timedelta(minutes=mins)).strftime('%Y-%m-%d %H:%M:%S')
        return None