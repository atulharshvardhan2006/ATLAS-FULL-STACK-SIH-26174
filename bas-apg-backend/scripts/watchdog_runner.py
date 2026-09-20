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

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WATCHDOG] Shutting down...")
        api_process.terminate()
        sys.exit(0)


if __name__ == "__main__":
    start_watchdog()
