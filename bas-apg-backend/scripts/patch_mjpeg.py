import os

engine_path = "/Users/atulharshvardhan/Desktop/clone/A.T.L.A.S/bas-apg/app/core/engine.py"
main_path = "/Users/atulharshvardhan/Desktop/clone/A.T.L.A.S/bas-apg/app/main.py"

# --- Patch engine.py ---
with open(engine_path, 'r') as f:
    engine_content = f.read()

# Add global_frame_buffer = None at the top
if "global_frame_buffer = None" not in engine_content:
    engine_content = engine_content.replace(
        "import numpy as np", 
        "import numpy as np\n\nglobal_frame_buffer = None"
    )

# Inject encoding logic inside the loop
target_code = "last_deviation_state = MissionState.fsm_deviation_flag"
injection = """last_deviation_state = MissionState.fsm_deviation_flag

        # MJPEG Global Buffer Inject
        global global_frame_buffer
        annotated_frame = frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if ret:
            global_frame_buffer = buffer.tobytes()"""

if target_code in engine_content and "MJPEG Global Buffer Inject" not in engine_content:
    engine_content = engine_content.replace(target_code, injection)

with open(engine_path, 'w') as f:
    f.write(engine_content)


# --- Patch main.py ---
with open(main_path, 'r') as f:
    main_content = f.read()

# 1. Update CORS
main_content = main_content.replace(
    'allow_methods=["GET", "POST"],', 
    'allow_methods=["*"],'
).replace(
    'allow_headers=["Content-Type", "Accept"],', 
    'allow_headers=["*"],'
)

# 2. Append Streaming Endpoint
new_endpoint = """
from fastapi.responses import StreamingResponse
import asyncio

async def frame_generator():
    while True:
        from app.core.engine import global_frame_buffer
        if global_frame_buffer is not None:
            yield (b'--frame\\r\\n'
                   b'Content-Type: image/jpeg\\r\\n\\r\\n' + global_frame_buffer + b'\\r\\n')
        await asyncio.sleep(0.03) # Cap at ~30 FPS to save Apple M4 thermal load

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
"""

if "async def frame_generator():" not in main_content:
    main_content += new_endpoint

with open(main_path, 'w') as f:
    f.write(main_content)

print("SUCCESS: Engine and Main patched with MJPEG global frame buffer.")
