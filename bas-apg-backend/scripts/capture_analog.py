"""
BAS-APG — Analog Video Capture for Microgravity Simulation

Usage:
    python scripts/capture_analog.py --output data/raw/videos --length 5
"""

import argparse
import os
import time

import cv2


def capture_clips(output_dir: str, clip_length_sec: int, camera_index: int = 0):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {camera_index}")
        return

    print("=" * 50)
    print(" Analog Video Capture Started")
    print(f" Target Clip Length: {clip_length_sec}s")
    print(" Press 'Space' to start recording a clip")
    print(" Press 'q' to quit")
    print("=" * 50)

    clip_count = 0
    recording = False
    start_time = 0
    out = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display_frame = frame.copy()

        if recording:
            elapsed = time.time() - start_time
            cv2.putText(
                display_frame,
                f"RECORDING {elapsed:.1f}s / {clip_length_sec}s",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )
            out.write(frame)

            if elapsed >= clip_length_sec:
                recording = False
                out.release()
                print(f"Saved clip {clip_count}")
                clip_count += 1
        else:
            cv2.putText(
                display_frame,
                "Ready - Press SPACE to record",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        cv2.imshow("Analog Capture", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            if not recording:
                recording = True
                start_time = time.time()
                clip_path = os.path.join(output_dir, f"clip_{clip_count:03d}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
                print(f"Recording {clip_path}...")

    if out is not None:
        out.release()
    cap.release()
    cv2.destroyAllWindows()
    print(f"Finished. Captured {clip_count} clips.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw/videos", help="Output directory")
    parser.add_argument("--length", type=int, default=5, help="Clip length in seconds")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()

    capture_clips(args.output, args.length, args.camera)


if __name__ == "__main__":
    main()
