<div align="center">
  
  <img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=800&size=40&pause=1000&color=00D8FF&center=true&vCenter=true&width=800&height=80&lines=A.T.L.A.S;Automated+Telemetry+%26+Logistics;Smart+India+Hackathon+2026;Zero-Error+Mission+Auditing" alt="Typing SVG" />

  <img src="https://img.shields.io/badge/SIH_2026-Project-00D8FF?style=for-the-badge&logo=rocket&logoColor=white" alt="SIH Project">
  <img src="https://img.shields.io/badge/Status-Flight_Ready-4CAF50?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Latency-<40ms-FF2A2A?style=for-the-badge" alt="Latency">
  
  <br />
  <br />

  <p align="center">
    <a href="#-overview">Overview</a> •
    <a href="#-frontend-calibration--hud-features">Frontend Features</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-offline-deployment-guide">Offline Deployment</a>
  </p>
</div>

<br/>

## 🌟 Overview
**A.T.L.A.S** is a highly robust, full-stack, AI-driven procedure monitoring system built for the **Smart India Hackathon (SIH)**. It ensures precision in complex tasks, such as scientific experiments (e.g., lunar soil titration, sample transfers), by acting as an intelligent auditing and telemetry agent.

Powered by real-time computer vision, A.T.L.A.S continuously tracks hand movements, objects, and kinematic states to guarantee that standard operating procedures (SOPs) are strictly followed. Deviations are instantly flagged visually and with voice alerts, ensuring zero-error mission execution.

---

## 🎛️ Frontend Calibration & HUD Features

The A.T.L.A.S frontend is not just a dashboard; it is a **Mission Control HUD** built with React and TailwindCSS. Before any mission begins, the system enforces a strict **Pre-Flight Hardware Lock** and calibration sequence.

### 🔬 Pre-Flight Setup & Calibration
- **Optical Intrinsic Matrix:** Live verification of `camera_profile.npz` (Focal Length & Distortion Centers `fx`, `fy`, `cx`).
- **Environmental Calibration Radar:** 
  - Real-time **Ambient Venue Lux** tracking with **Auto-CLAHE** priming.
  - **Optical Glare Saturation** monitoring via the proprietary **Glare Guardian** system.
- **PID Thermodynamic Baseline:** Live Edge Node Idle Temp and stable FPS tracking.
- **Mass Manifest Lock (FOD):** AI Vision must detect and verify all physical payload items (e.g., *Lunar Regolith Sample, Titration Flask*) before the State Machine unlocks the mission sequence.

### 🛰️ Live Mission HUD
- **Real-time MJPEG Decoding:** High-FPS, ultra-low latency optical stream parsing directly from the edge node.
- **AI Confidence Mocking:** Live telemetry charts reflecting the YOLOv8 and MediaPipe structural confidence metrics.
- **OVERDUE UI Matrix:** Dynamic timers and SLA alerts that warn the operator if a specific procedural step is taking longer than the standard baseline.
- **WebSocket Synchronization:** Instant state reconciliation between the Python backend FSM and the React UI.

---

## ✨ Backend & AI Capabilities

- 👁️ **Multi-Model Tracking**: Fuses `YOLOv8` object detection with `MediaPipe` 3D skeletal landmarker.
- ⚙️ **Finite State Machine (FSM)**: Enforces procedural workflows defined in modular `JSON` configurations.
- 📐 **Kinematic PnP Solving**: Measures precise spatial deviations and interaction angles in 3D space.
- 🎙️ **Voice Alerts**: Delivers instant auditory feedback (e.g., *"Warning: Hand detected without gloves"*).

---

## 🛠️ Tech Stack

<div align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,react,ts,tailwind,opencv,sqlite,vite&theme=dark" />
  </a>
</div>

<br/>

---

## 🚀 Offline Deployment Guide

For SIH presentations, reliable offline capability is critical. A.T.L.A.S is designed to run entirely locally without external API dependencies. All base ML models (`yolov8n.pt` and `hand_landmarker.task`) are included in this repository.

<details>
<summary><b>1. Environment Preparation (Click to Expand)</b></summary>

Ensure you have the following installed on your edge node or presentation machine:
- **Python 3.10+**
- **Node.js 18+** & npm
- A connected USB Webcam or integrated camera.
</details>

<details>
<summary><b>2. Backend (Edge Node) Offline Setup</b></summary>

The backend powers the heavy lifting (YOLO, MediaPipe, FSM, and FastAPI WebSocket server).

```bash
# Navigate to the backend directory
cd bas-apg-backend

# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the vision engine and telemetry server
# Note: Models are already bundled locally! No downloads required.
./launch_edge_node.sh
```
*(The backend runs on `localhost:8000`)*
</details>

<details>
<summary><b>3. Frontend (Telemetry HUD) Offline Setup</b></summary>

The frontend operates locally using Vite and connects to the backend WebSockets.

```bash
# Navigate to the frontend directory
cd bas-apg-frontend

# Install Node dependencies (Requires internet only for the first installation)
npm install

# Start the Vite development server
npm run dev
```
*(The frontend runs on `localhost:5173`)*
</details>

<details>
<summary><b>4. One-Click Launch (macOS/Linux)</b></summary>

For rapid presentation recovery, use the bundled concurrent startup script:

```bash
chmod +x launch_demo.sh
./launch_demo.sh
```
This script will instantly spawn both the backend telemetry server and the React Mission Control HUD.
</details>

---

<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=00D8FF&height=120&section=footer"/>
</div>
