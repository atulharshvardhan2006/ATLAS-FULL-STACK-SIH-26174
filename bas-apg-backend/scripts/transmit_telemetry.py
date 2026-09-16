"""
BAS-APG — IDSN Telemetry Compression (Phase 17)

Converts a verbose JSON log of the FSM into a highly optimized
Protocol Buffers binary payload to meet IDSN bandwidth limits (<50KB).

Usage:
    python scripts/transmit_telemetry.py
"""

import json
import os
import sys

# Ensure protobuf is compiled
try:
    from app.schemas import telemetry_pb2
except ImportError:
    print(
        "ERROR: Protobuf bindings not found. Please run `python scripts/compile_proto.py` first."
    )
    sys.exit(1)


def simulate_json_log(output_json: str):
    """Generate a bulky dummy JSON log to simulate a 30-min experiment."""
    log = {"procedure_name": "red_yellow_box_transfer", "frames": []}

    print("Generating simulated JSON telemetry log (600 frames)...")
    # Simulate 600 frames
    for i in range(600):
        frame = {
            "timestamp": 1690000000.0 + i,
            "fsm_state": {
                "current_step_id": "step_1" if i < 300 else "step_2",
                "status": "IN_PROGRESS",
                "start_time": "1690000000.0",
                "recovery_text": "",
            },
            "detections": [
                {
                    "class_name": "Tweezers",
                    "confidence": 0.95,
                    "track_id": 1,
                    "bbox_cx": 320.5,
                    "bbox_cy": 240.5,
                    "bbox_w": 50.0,
                    "bbox_h": 10.0,
                },
                {
                    "class_name": "Red_Box",
                    "confidence": 0.88,
                    "track_id": 2,
                    "bbox_cx": 100.0,
                    "bbox_cy": 100.0,
                    "bbox_w": 80.0,
                    "bbox_h": 80.0,
                },
            ],
            "interactions": [
                {
                    "class_name": "Tweezers",
                    "state": "HELD" if i > 150 else "NEAR",
                    "distance_mm": 15.5,
                }
            ],
            "latency_ms": 35,
            "fps": 30,
        }
        log["frames"].append(frame)

    with open(output_json, "w") as f:
        json.dump(log, f, indent=2)

    print(f"JSON Log created: {output_json}")


def compress_to_protobuf(input_json: str, output_bin: str):
    """Parse JSON log and serialize into binary Protobuf format."""
    print(f"\nCompressing {input_json} to {output_bin}...")

    with open(input_json, "r") as f:
        json_log = json.load(f)

    proto_log = telemetry_pb2.TelemetryLog()
    proto_log.procedure_name = json_log.get("procedure_name", "")

    for json_frame in json_log.get("frames", []):
        proto_frame = proto_log.frames.add()
        proto_frame.timestamp = json_frame.get("timestamp", 0.0)
        proto_frame.latency_ms = json_frame.get("latency_ms", 0)
        proto_frame.fps = json_frame.get("fps", 0)

        state = json_frame.get("fsm_state", {})
        proto_frame.fsm_state.current_step_id = state.get("current_step_id", "")
        proto_frame.fsm_state.status = state.get("status", "")
        proto_frame.fsm_state.start_time = state.get("start_time", "")
        proto_frame.fsm_state.recovery_text = state.get("recovery_text", "")

        for json_det in json_frame.get("detections", []):
            proto_det = proto_frame.detections.add()
            proto_det.class_name = json_det.get("class_name", "")
            proto_det.confidence = json_det.get("confidence", 0.0)
            proto_det.track_id = json_det.get("track_id", 0)
            proto_det.bbox_cx = json_det.get("bbox_cx", 0.0)
            proto_det.bbox_cy = json_det.get("bbox_cy", 0.0)
            proto_det.bbox_w = json_det.get("bbox_w", 0.0)
            proto_det.bbox_h = json_det.get("bbox_h", 0.0)

        for json_int in json_frame.get("interactions", []):
            proto_int = proto_frame.interactions.add()
            proto_int.class_name = json_int.get("class_name", "")
            proto_int.state = json_int.get("state", "")
            proto_int.distance_mm = json_int.get("distance_mm", 0.0)

    # Serialize to string (bytes)
    binary_payload = proto_log.SerializeToString()

    with open(output_bin, "wb") as f:
        f.write(binary_payload)

    print(f"Binary Telemetry Payload created: {output_bin}")

    # Calculate Compression
    json_size = os.path.getsize(input_json)
    bin_size = os.path.getsize(output_bin)

    print("\n" + "=" * 60)
    print(" IDSN Deep-Space Telemetry Compression Results")
    print("=" * 60)
    print(f" Original JSON Size:   {json_size / 1024:.2f} KB")
    print(f" Protobuf Binary Size: {bin_size / 1024:.2f} KB")
    print(f" Compression Ratio:    {json_size / bin_size:.2f}x smaller")
    print(f" Space Saved:          {(1 - bin_size/json_size)*100:.1f}%")
    if bin_size < 50000:
        print(" STATUS: ✅ PASSED (<50 KB IDSN Bandwidth Limit)")
    else:
        print(" STATUS: ❌ FAILED (Exceeds 50 KB)")
    print("=" * 60)


def main():
    os.makedirs("data/telemetry", exist_ok=True)
    json_path = "data/telemetry/simulated_log.json"
    bin_path = "data/telemetry/payload.bin"

    simulate_json_log(json_path)
    compress_to_protobuf(json_path, bin_path)


if __name__ == "__main__":
    main()
