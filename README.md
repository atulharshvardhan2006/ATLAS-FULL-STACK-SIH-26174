<div align="center">
  <img src="https://img.shields.io/badge/SIH_2026-Project-blue?style=for-the-badge" alt="SIH Project">
  
  <br />
  <br />

  # 🚀 A.T.L.A.S (Automated Telemetry & Logistics Analysis System)
  
  **An Advanced Computer Vision Platform for Automated Procedure Tracking and Mission Auditing**

  <p align="center">
    <a href="#overview">Overview</a> •
    <a href="#key-features">Key Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#system-architecture">System Architecture</a> •
    <a href="#getting-started">Getting Started</a>
  </p>
</div>

<br/>

## 🌟 Overview
**A.T.L.A.S** is a highly robust, full-stack, AI-driven procedure monitoring system built for the Smart India Hackathon (SIH). It ensures precision in complex tasks, such as scientific experiments (e.g., lunar soil titration, sample transfers), by acting as an intelligent auditing and telemetry agent.

Powered by real-time computer vision, A.T.L.A.S continuously tracks hand movements, objects, and kinematic states to guarantee that standard operating procedures (SOPs) are strictly followed. Deviations are instantly flagged visually and with voice alerts, ensuring zero-error mission execution.

---

## ✨ Key Features

- 👁️ **Real-time Object & Pose Tracking**: Employs cutting-edge `YOLOv8` and `MediaPipe` models to accurately track objects, hands, and human interaction simultaneously.
- ⚙️ **Intelligent Finite State Machine (FSM)**: Enforces procedural workflows and tracks progress dynamically through complex multi-step experiments.
- 📐 **Kinematic Analysis & PnP Solving**: Measures precise spatial deviations and angles in 3D space, preventing critical handling errors.
- 🎙️ **Voice Alerts & Visual HUD**: Provides instant feedback during procedure deviations (e.g., "Warning: Hand detected without gloves" or "Incorrect sequence!").
- 📊 **Live Telemetry & Auditing**: A beautiful React frontend providing real-time data streaming, confidence scores, and overdue step alerts for remote monitoring.

---

## 🛠️ Tech Stack

### 🧠 Backend (Edge Engine)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi) ![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=for-the-badge&logo=opencv&logoColor=white) 
- **Core Framework**: Python, FastAPI
- **Computer Vision**: OpenCV, Ultralytics (YOLOv8), MediaPipe Hand Landmarker
- **Algorithms**: ORB feature matching, Kalman Filters, Perspective-n-Point (PnP) Solver
- **Data & Telemetry**: SQLite, Protocol Buffers (gRPC/Proto)

### 💻 Frontend (Telemetry Dashboard)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB) ![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white) ![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)
- **Core Framework**: React (Vite)
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom premium typography (JetBrains Mono, Orbitron)
- **Features**: Live MJPEG video stream decoding, HUD overlays, WebSocket-ready states

---

## 🏗️ System Architecture

A.T.L.A.S operates on a split Edge-Cloud architecture optimized for low-latency visual tracking:

1. **Hardware / Camera Interface**: Captures analog and digital webcam feeds at high frame rates.
2. **Vision Pipeline (Backend)**: Analyzes frames in parallel. Extracts bounding boxes (YOLO), feature descriptors (ORB), and skeletal nodes (MediaPipe).
3. **Core Engine**: The `procedure_fsm` cross-references live data with expected SOP configurations defined in `JSON` formats. Deviations are triggered through the `deviation_detector`.
4. **Dashboard (Frontend)**: Consumes backend streams and visualizes the exact mission state and telemetry for mission control operators.

---

## 🚀 Getting Started (Deployment)

These instructions will get your copy of the project up and running on your local edge node or laptop.

### 1. Prerequisites
Ensure you have the following installed:
- Python 3.10+
- Node.js 18+ & npm
- Git

### 2. Backend Setup
```bash
# Navigate to the backend directory
cd bas-apg-backend

# Install Python dependencies
pip install -r requirements.txt

# Start the vision engine and telemetry server
./launch_edge_node.sh
# OR run the python script directly
python app/main.py
```

### 3. Frontend Setup
```bash
# Navigate to the frontend directory
cd bas-apg-frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

### 4. Running the Complete Demo
We've included an automated launch script that fires up both the engine and the UI concurrently for easy demonstration:
```bash
./launch_demo.sh
```

---

<div align="center">
  <i>Developed with ❤️ for the Smart India Hackathon.</i>
</div>
