"""
BAS-APG — Backend ML Server Test Script

Tests the REST endpoints and WebSocket stream of the backend ML server.
"""

import asyncio
import json
import time

import requests
import websockets

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/live"


def test_rest_endpoints():
    print("=" * 60)
    print("  1. TESTING REST API ENDPOINTS")
    print("=" * 60)

    # 1. Health Check
    print("\n[TEST] GET /health")
    try:
        r = requests.get(f"{API_URL}/health")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Initial State
    print("\n[TEST] GET /api/state (Before Start)")
    try:
        r = requests.get(f"{API_URL}/api/state")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Start Procedure
    print("\n[TEST] POST /api/start")
    try:
        r = requests.post(f"{API_URL}/api/start")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. State After Start
    print("\n[TEST] GET /api/state (After Start)")
    try:
        r = requests.get(f"{API_URL}/api/state")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")


async def test_websocket():
    print("\n" + "=" * 60)
    print("  2. TESTING WEBSOCKET ML PIPELINE STREAM")
    print("=" * 60)

    print(f"\n[TEST] Connecting to {WS_URL} ...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to ML Stream WebSocket!")

            # Receive 3 payloads to prove continuous streaming
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)

                print(f"\n--- WS Payload {i+1} ---")
                print(f"Timestamp: {data.get('timestamp')}")
                print(f"FPS: {data.get('fps')}")

                # We don't print the huge base64 frame, just length
                frame_len = len(data.get("frame", ""))
                print(f"Frame (Base64 JPEG): {frame_len} bytes")

                print(f"Detections (YOLO): {len(data.get('detections', []))} objects")
                print(
                    f"Interactions (HOI): {len(data.get('interactions', []))} objects"
                )

                state = data.get("state", {})
                print(
                    f"FSM Status: {state.get('status')} | Step: {state.get('current_step')} | Expects: {state.get('expected_action')} {state.get('expected_object')}"
                )

                # Small delay between frames
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"WebSocket Error: {e}")


if __name__ == "__main__":
    test_rest_endpoints()

    # Run the async websocket test
    asyncio.run(test_websocket())

    print("\n✅ All Backend Tests Completed!")
