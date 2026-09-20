import asyncio
import time
import cv2
import math
import numpy as np
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.core.state import MissionState  

router = APIRouter()


async def generate_mjpeg_stream():
    last_seq = -1
    local_mjpeg_buffer = np.zeros((1080, 1920, 3), dtype=np.uint8)
    try:
        while True:
            current_seq = MissionState.frame_sequence
            if current_seq == last_seq:
                await asyncio.sleep(0.005)
                continue

            last_seq = current_seq
            frame = MissionState.latest_frame
            if frame is None:
                continue

            if frame.shape == local_mjpeg_buffer.shape:
                np.copyto(local_mjpeg_buffer, frame)
            else:
                local_mjpeg_buffer = frame.copy()

            ret, buffer = await asyncio.to_thread(
                cv2.imencode, '.jpg', local_mjpeg_buffer, [cv2.IMWRITE_JPEG_QUALITY, 70]
            )
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + frame_bytes
                + b'\r\n'
            )
    except (GeneratorExit, ConnectionError, asyncio.CancelledError):
        pass

@router.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


def sanitize_float(val):
    return 0.0 if val is None or math.isnan(val) or math.isinf(val) else val

@router.websocket("/ws/telemetry/{session_id}")
async def telemetry_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    MissionState.active_session_id = session_id
    
    TARGET_FRAME_TIME = 1.0 / 30.0
    next_frame_deadline = time.perf_counter()

    try:
        while True:
            next_frame_deadline += TARGET_FRAME_TIME

            S = MissionState

            payload = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "system_status": S.system_status,
                "auth_status": S.auth_status,
                "isp_settling": S.isp_settling,
                "isp_remaining_s": round(S.isp_remaining_s, 1),
                "standby_mode": S.standby_mode,
                "fps": round(S.fps, 1),
                "inference_ms": round(S.inference_ms, 1),
                "detections": S.yolo_detections,
                "hand": {
                    "detected": S.hand_detected,
                    "norm_wrist": S.hand_wrist,
                    "norm_fingertip": S.hand_fingertip,
                    "velocity_mm_s": round(S.hand_velocity, 1),
                    "is_immobile": S.hand_is_immobile,
                },
                "hoi": {
                    "pearson_r": round(sanitize_float(S.pearson_r), 2),
                    "is_grasping": S.is_grasping,
                    "grasped_object": S.grasped_object,
                },
                "fsm": {
                    "current_state": S.fsm_current_state,
                    "previous_state": S.fsm_previous_state,
                    "procedure_step": S.fsm_current_step,
                    "total_steps": S.fsm_total_steps,
                    "deviation_flag": S.fsm_deviation_flag,
                    "deviation_details": S.fsm_deviation_details,
                    "debounce_progress": S.fsm_debounce_count,
                    "expected_action": S.fsm_expected_action,
                    "expected_object": S.fsm_expected_object,
                },
                "spatial": {
                    "aruco_detected": S.aruco_detected,
                    "z_offset_mm": round(S.z_offset_mm, 1),
                    "z_boundary_mm": round(S.z_boundary_mm, 1),
                    "norm_boundary_y": round(S.norm_boundary_y, 3),
                    "containment_breach": S.containment_breach,
                },
                "glare": {
                    "saturation_pct": round(S.glare_saturation, 2),
                    "is_blinded": S.is_blinded,
                    "kalman_coasting": S.kalman_coasting,
                    "coast_frames": S.kalman_coast_frames,
                },
                "system": {
                    "ram_usage_mb": S.ram_usage_mb,
                    "ram_total_mb": 16384,
                    "usb_status": S.usb_status,
                    "logs": list(S.recent_logs),
                },
            }

            try:
                await websocket.send_json(payload)
            except Exception:
                break

            now = time.perf_counter()
            if now > next_frame_deadline:
                next_frame_deadline = now
                
            sleep_duration = max(0.0, next_frame_deadline - now)
            await asyncio.sleep(sleep_duration)

    except WebSocketDisconnect:
        pass

@router.post("/api/fsm/override")
def wizard_override():
    """Wizard of Oz override to force the FSM to advance to the next step."""
    MissionState.fsm_wizard_override = True
    return {"status": "ok", "message": "Wizard override triggered"}

@router.post("/api/auth/start_scan")
def start_auth_scan():
    """Trigger the backend to start face recognition."""
    MissionState.auth_status = "SCANNING"
    return {"status": "ok", "message": "Scanning initiated"}
