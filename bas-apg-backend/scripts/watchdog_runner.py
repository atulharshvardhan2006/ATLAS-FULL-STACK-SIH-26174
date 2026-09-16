"""
BAS-APG — Multi-Process Watchdog Runner

Spawns and monitors the isolated ML process and the FastAPI server.
If the ML process crashes (e.g. OOM, segfault), it is instantly restarted.
The FSM state is preserved on disk, so it resumes exactly where it left off.
"""

import multiprocessing
import os
import subprocess
import sys
import time

import uvicorn

from app.core.engine import run_ai_engine
from app.main import app


def start_api():
    """Run the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def start_watchdog():
    print("=" * 60)
    print("  BAS-APG Watchdog Runner Initializing...")
    print("=" * 60)

    # Clean up old state
    if os.path.exists("/tmp/bas_apg_state.json"):
        os.remove("/tmp/bas_apg_state.json")

    # Start API in a separate process
    api_process = multiprocessing.Process(target=start_api)
    api_process.start()

    ml_process = None

    try:
        while True:
            if ml_process is None or not ml_process.is_alive():
                if ml_process is not None:
                    print("\n[WATCHDOG] 🚨 ML Process Crash Detected! 🚨")
                    print("[WATCHDOG] Restarting ML pipeline to resume state...\n")
                    time.sleep(1)  # Brief pause before restart

                ml_process = multiprocessing.Process(target=run_ai_engine)
                ml_process.start()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[WATCHDOG] Shutting down...")
        if ml_process:
            ml_process.terminate()
        api_process.terminate()
        sys.exit(0)


if __name__ == "__main__":
    start_watchdog()
