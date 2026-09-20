import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import stream, session, object_registry, procedure_builder

app = FastAPI(title="BAS-APG Telemetry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream.router)
app.include_router(session.router)
app.include_router(object_registry.router)
app.include_router(procedure_builder.router)


@app.on_event("startup")
def boot_engines():
    from app.core.engine import run_ai_engine
    threading.Thread(target=run_ai_engine, daemon=True).start()

@app.on_event("shutdown")
def shutdown_db():
    from app.core.database import flight_recorder_queue, get_connection
    
    flight_recorder_queue.join()
    
    conn = get_connection()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

from fastapi.responses import StreamingResponse
import asyncio

async def frame_generator():
    while True:
        from app.core.engine import global_frame_buffer
        if global_frame_buffer is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + global_frame_buffer + b'\r\n')
        await asyncio.sleep(0.03) 

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


from fastapi.responses import FileResponse
import os

@app.get("/api/session/{session_id}/recording")
async def get_session_recording(session_id: str):
    """Serve the recorded MP4 video for a completed session."""
    import glob
    recordings_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'experiment_videos')
    list_of_files = glob.glob(os.path.join(recordings_dir, '*.mp4'))
    if not list_of_files:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Recording not found"})
    latest_file = max(list_of_files, key=os.path.getctime)
    return FileResponse(latest_file, media_type="video/mp4", filename=os.path.basename(latest_file))

@app.post("/start_demo")
async def start_demo():
    from app.core.state import MissionState
    MissionState.reset_fsm_flag = True
    MissionState.demo_started = True
    return {"status": "started"}

@app.post("/end_demo")
async def end_demo():
    from app.core.state import MissionState
    MissionState.demo_started = False
    MissionState.active_session_id = None
    return {"status": "ended"}


@app.post("/api/fsm/set_target")
async def set_target(object: str):
    from app.core.state import MissionState
    MissionState.frontend_target = object
    return {"status": "ok", "target": object}

from pydantic import BaseModel
class SpeakRequest(BaseModel):
    text: str

@app.post("/api/speak")
async def trigger_speak(req: SpeakRequest):
    from app.core.engine import speak
    speak(req.text)
    return {"status": "spoken"}
