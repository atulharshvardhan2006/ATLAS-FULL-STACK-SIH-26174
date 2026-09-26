import sqlite3
import queue
import threading
from datetime import datetime, timezone

import os
import shutil
import time
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()
DB_PATH = settings.db_path


os.makedirs(Path(DB_PATH).parent, exist_ok=True)

_thread_local = threading.local()

def get_connection() -> sqlite3.Connection:
    """Returns a thread-local connection with edge-optimized PRAGMAs applied.
    
    Each thread (FastAPI workers, DB writer daemon) gets exactly one
    persistent connection. Eliminates open/close overhead at 30 Hz.
    """
    if not hasattr(_thread_local, 'conn') or _thread_local.conn is None:
        _thread_local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _thread_local.conn.execute("PRAGMA journal_mode=WAL;")       
        _thread_local.conn.execute("PRAGMA synchronous=NORMAL;")      
        _thread_local.conn.execute("PRAGMA temp_store=MEMORY;")        
        _thread_local.conn.execute("PRAGMA foreign_keys=ON;")  
    return _thread_local.conn

def init_db():
    """Initializes and verifies the database, recovering if corrupt."""
    global DB_PATH
    
    
    if os.path.exists(DB_PATH):
        try:
            test_conn = sqlite3.connect(DB_PATH)
            result = test_conn.execute("PRAGMA quick_check;").fetchone()
            test_conn.close()
            if result[0] != "ok":
                raise sqlite3.DatabaseError("Corrupted database")
        except Exception:
            corrupt_backup = f"{DB_PATH}.corrupt_{int(time.time())}"
            print(f"⚠️ DATABASE CORRUPT! Archiving to {corrupt_backup} and rebuilding fresh.")
            shutil.move(DB_PATH, corrupt_backup)

    
    conn = get_connection()
    
    
    conn.execute("PRAGMA auto_vacuum = INCREMENTAL;")
    
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bas_sessions (
            session_id    TEXT PRIMARY KEY,
            operator_name TEXT NOT NULL,
            protocol_id   TEXT NOT NULL,
            start_time    TEXT NOT NULL,
            end_time      TEXT,
            total_deviations INTEGER DEFAULT 0
        )
    """)
    
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fsm_transitions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            previous_state TEXT NOT NULL,
            new_state     TEXT NOT NULL,
            merkle_hash   TEXT DEFAULT '',
            FOREIGN KEY (session_id) REFERENCES bas_sessions(session_id)
        )
    """)
    
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hazard_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            hazard_type   TEXT NOT NULL,
            resolved_time TEXT,
            FOREIGN KEY (session_id) REFERENCES bas_sessions(session_id)
        )
    """)
    
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fsm_session ON fsm_transitions(session_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hazard_session ON hazard_logs(session_id);")
    
    conn.commit()
    

flight_recorder_queue = queue.Queue()

def db_writer_daemon():
    """
    Dedicated background thread that drains the queue and writes to SQLite.
    The main AI loop calls flight_recorder_queue.put() which takes ~0.0001ms
    and never blocks YOLO inference.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    while True:
        event = flight_recorder_queue.get()
        if event is None:
            break  
        
        table, data = event
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            if table == "FSM":
                cursor.execute(
                    "INSERT INTO fsm_transitions (session_id, timestamp, previous_state, new_state, merkle_hash) VALUES (?, ?, ?, ?, ?)",
                    (data["session_id"], now, data["previous_state"], data["new_state"], data.get("merkle_hash", ""))
                )
            elif table == "HAZARD":
                cursor.execute(
                    "INSERT INTO hazard_logs (session_id, timestamp, hazard_type) VALUES (?, ?, ?)",
                    (data["session_id"], now, data["hazard_type"])
                )
            elif table == "RESOLVE_HAZARD":
                cursor.execute(
                    """
                    UPDATE hazard_logs 
                    SET resolved_time = ? 
                    WHERE session_id = ? AND hazard_type = ? AND resolved_time IS NULL
                    """,
                    (now, data["session_id"], data["hazard_type"])
                )
            conn.commit()
        except Exception as e:
            conn.rollback()  
            print(f"DB_WRITER ERROR: {e}")
        
        flight_recorder_queue.task_done()
    
    conn.close()

def prune_old_sessions(retention_limit: int = 100):
    """Keeps the most recent N sessions and cleans up orphaned foreign records."""
    conn = get_connection()
    try:
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id FROM bas_sessions 
            ORDER BY start_time DESC 
            LIMIT -1 OFFSET ?
        """, (retention_limit,))
        old_ids = [row[0] for row in cursor.fetchall()]
        
        if old_ids:
            placeholders = ",".join("?" * len(old_ids))
            cursor.execute(f"DELETE FROM fsm_transitions WHERE session_id IN ({placeholders})", old_ids)
            cursor.execute(f"DELETE FROM hazard_logs WHERE session_id IN ({placeholders})", old_ids)
            cursor.execute(f"DELETE FROM bas_sessions WHERE session_id IN ({placeholders})", old_ids)
            conn.commit()
            cursor.execute("PRAGMA incremental_vacuum;")
    except Exception as e:
        conn.rollback()
        print(f"DB_PRUNE ERROR: {e}")


init_db()
threading.Thread(target=db_writer_daemon, daemon=True).start()
