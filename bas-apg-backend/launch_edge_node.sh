#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# BAS-APG Edge Node — One-Click Deployment Script
# Target: Apple Silicon M4 (16GB) / macOS
# Usage:  chmod +x launch_edge_node.sh && ./launch_edge_node.sh
# ═══════════════════════════════════════════════════════════════════

set -e  # Exit immediately on any error

echo "═══════════════════════════════════════════════════════════"
echo "  BAS-APG Edge Node — Ignition Sequence"
echo "  Target Hardware: Apple Silicon M4 (Unified Memory)"
echo "═══════════════════════════════════════════════════════════"

# ── 1. Activate Conda Environment ──
echo ""
echo "[1/4] Activating conda environment..."
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
    source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
else
    echo "WARNING: conda.sh not found. Attempting 'conda' from PATH..."
fi

conda activate bas_apg_env 2>/dev/null || {
    echo "Environment 'bas_apg_env' not found. Creating it now..."
    conda create -n bas_apg_env python=3.11 -y
    conda activate bas_apg_env
}

echo "  ✅ Environment: $(python --version) @ $(which python)"

# ── 2. Hydrate Dependencies ──
echo ""
echo "[2/4] Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet

echo "  ✅ All packages installed (including scipy for HOI Pearson correlation)"

# ── 3. Verify Critical Imports ──
echo ""
echo "[3/4] Pre-flight import check..."
python -c "
import cv2; print(f'  OpenCV:      {cv2.__version__}')
import numpy; print(f'  NumPy:       {numpy.__version__}')
import torch; print(f'  PyTorch:     {torch.__version__}')
import ultralytics; print(f'  Ultralytics: {ultralytics.__version__}')
import mediapipe; print(f'  MediaPipe:   {mediapipe.__version__}')
import fastapi; print(f'  FastAPI:     {fastapi.__version__}')
import scipy; print(f'  SciPy:       {scipy.__version__}')
print('  ✅ All critical imports verified')
" || {
    echo "  ❌ Import check failed. Run 'pip install -r requirements.txt' manually."
    exit 1
}

# ── 4. Ignite the ASGI Server ──
echo ""
echo "[4/4] Igniting FastAPI RTOS on 127.0.0.1:8000..."
echo "═══════════════════════════════════════════════════════════"
echo "  MJPEG Feed:     http://127.0.0.1:8000/video_feed"
echo "  Telemetry WS:   ws://127.0.0.1:8000/ws/telemetry/{id}"
echo "  Session API:    http://127.0.0.1:8000/api/session/start"
echo "═══════════════════════════════════════════════════════════"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port 8000
