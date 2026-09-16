"""
BAS-APG — Camera Calibration Script

Calculates intrinsic camera parameters (focal length, distortion coefficients)
using a standard checkerboard pattern.

Usage:
    python scripts/calibrate_camera.py --square_size 25 --output data/camera_calibration.json
"""

import argparse
import json
import os

import cv2
import numpy as np


def calibrate_camera(square_size_mm: float, output_path: str, camera_index: int = 0):
    # Checkerboard dimensions (internal corners)
    CHECKERBOARD = (6, 9)

    # termination criteria for subpixel corner detection
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # Prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[0, :, :2] = np.mgrid[0 : CHECKERBOARD[0], 0 : CHECKERBOARD[1]].T.reshape(-1, 2)
    objp = objp * square_size_mm

    # Arrays to store object points and image points from all the images.
    objpoints = []  # 3d point in real world space
    imgpoints = []  # 2d points in image plane.

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {camera_index}")
        return

    print("=" * 50)
    print(" Camera Calibration Started")
    print(" Show a checkerboard pattern (9x6 internal corners) to the camera.")
    print(" Press 'Space' to capture a calibration frame.")
    print(" Need at least 10-15 frames from different angles.")
    print(" Press 'c' to compute calibration and exit.")
    print(" Press 'q' to quit without saving.")
    print("=" * 50)

    captured_frames = 0
    img_shape = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if img_shape is None:
            img_shape = gray.shape[::-1]

        # Find the chess board corners
        ret_corners, corners = cv2.findChessboardCorners(
            gray,
            CHECKERBOARD,
            cv2.CALIB_CB_ADAPTIVE_THRESH
            + cv2.CALIB_CB_FAST_CHECK
            + cv2.CALIB_CB_NORMALIZE_IMAGE,
        )

        display_frame = frame.copy()

        if ret_corners:
            # Draw the corners
            cv2.drawChessboardCorners(display_frame, CHECKERBOARD, corners, ret_corners)
            cv2.putText(
                display_frame,
                "Checkerboard Detected! Press SPACE to capture.",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
        else:
            cv2.putText(
                display_frame,
                "Looking for checkerboard...",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        cv2.putText(
            display_frame,
            f"Captured: {captured_frames}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

        cv2.imshow("Calibration", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("Calibration aborted.")
            break
        elif key == ord(" ") and ret_corners:
            # Refine corner locations
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            objpoints.append(objp)
            imgpoints.append(corners2)
            captured_frames += 1
            print(f"Captured frame {captured_frames}")
        elif key == ord("c"):
            if captured_frames < 5:
                print("Not enough frames. Capture at least 5 (10-15 recommended).")
                continue

            print("\nCalculating calibration matrix...")
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, img_shape, None, None
            )

            if ret:
                calibration_data = {
                    "camera_matrix": mtx.tolist(),
                    "dist_coeffs": dist.tolist(),
                    "rms_error": ret,
                    "image_width": img_shape[0],
                    "image_height": img_shape[1],
                }

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(calibration_data, f, indent=4)

                print(f"✅ Calibration successful! RMS Error: {ret:.4f}")
                print(f"Saved calibration data to {output_path}")
            else:
                print("❌ Calibration failed.")
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--square_size", type=float, default=25.0, help="Square size in mm"
    )
    parser.add_argument(
        "--output", default="data/camera_calibration.json", help="Output JSON path"
    )
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()

    calibrate_camera(args.square_size, args.output, args.camera)


if __name__ == "__main__":
    main()
