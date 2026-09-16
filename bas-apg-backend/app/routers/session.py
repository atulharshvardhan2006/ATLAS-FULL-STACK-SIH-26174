import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.database import get_connection, flight_recorder_queue
from app.core.state import MissionState

router = APIRouter()

class SessionStartRequest(BaseModel):
    operator_name: str = Field(..., max_length=100)
    protocol_id: str = Field(..., max_length=100)

@router.post("/api/session/start")
async def start_session(req: SessionStartRequest):
    session_id = f"BAS-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection()
    conn.execute(
        "INSERT INTO bas_sessions (session_id, operator_name, protocol_id, start_time) VALUES (?, ?, ?, ?)",
        (session_id, req.operator_name, req.protocol_id, now)
    )
    conn.commit()
    
    
    return {"session_id": session_id, "status": "HARDWARE_PRIMED"}

@router.post("/api/session/{session_id}/stop")
async def stop_session(session_id: str):
    """
    FIX 44: Ghost Hardware Lock.
    """
    MissionState.active_session_id = None
    
    await asyncio.to_thread(flight_recorder_queue.join)
    
    now = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM hazard_logs WHERE session_id = ? AND hazard_type = 'SEQUENCE_DEVIATION'",
        (session_id,)
    ).fetchone()
    total_deviations = row[0] if row else 0
    
    conn.execute(
        "UPDATE bas_sessions SET end_time = ?, total_deviations = ? WHERE session_id = ?",
        (now, total_deviations, session_id)
    )
    conn.commit()
    
    return {"status": "HARDWARE_SLEEPING"}

@router.get("/api/session/{session_id}/audit")
async def get_session_audit(session_id: str):
    conn = get_connection()
    
    session = conn.execute(
        "SELECT operator_name, total_deviations FROM bas_sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    
    transitions = conn.execute(
        "SELECT timestamp, previous_state, new_state FROM fsm_transitions WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    
    hazards = conn.execute(
        "SELECT timestamp, hazard_type FROM hazard_logs WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    
    
    timeline = []
    for t in transitions:
        timeline.append({
            "timestamp": t[0],
            "type": "INFO",
            "action": f"FSM: {t[1]} → {t[2]}"
        })
    for h in hazards:
        timeline.append({
            "timestamp": h[0],
            "type": "CRITICAL",
            "action": f"HAZARD: {h[1]}"
        })
    
    timeline.sort(key=lambda e: e["timestamp"])
    
    import os, glob
    recordings_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'experiment_videos')
    list_of_files = glob.glob(os.path.join(recordings_dir, '*.mp4'))
    file_size_mb = 0
    if list_of_files:
        latest_file = max(list_of_files, key=os.path.getctime)
        file_size_mb = round(os.path.getsize(latest_file) / (1024 * 1024), 2)
        
    return {
        "session_id": session_id,
        "operator_name": session[0] if session else "Unknown",
        "total_deviations": session[1] if session else 0,
        "timeline": timeline,
        "file_size_mb": file_size_mb
    }

@router.get("/api/sessions")
async def get_all_sessions():
    """Returns a list of all recorded sessions for the dashboard."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT session_id, operator_name, protocol_id, start_time, end_time, total_deviations FROM bas_sessions ORDER BY start_time DESC"
    ).fetchall()
    
    return {
        "sessions": [
            {
                "session_id": s[0],
                "operator_name": s[1],
                "protocol_id": s[2],
                "start_time": s[3],
                "end_time": s[4],
                "total_deviations": s[5]
            } for s in sessions
        ]
    }
