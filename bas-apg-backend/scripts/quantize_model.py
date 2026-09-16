"""
BAS-APG — YOLO Model Quantization

Exports the trained YOLO model to ONNX format with FP16 precision.
This significantly reduces memory footprint and increases inference speed on edge CPUs.

Usage:
    python scripts/quantize_model.py --weights data/models/best.pt
"""

import argparse
import os

from ultralytics import YOLO


def quantize(weights_path: str):
    if not os.path.exists(weights_path):
        print(f"ERROR: Model weights not found at {weights_path}")
        return

    print(f"Loading model from {weights_path}")
    model = YOLO(weights_path)

    print("Exporting to ONNX format with FP16 precision (half=True)...")
    model.export(format="onnx", half=True, dynamic=False)

    print("✅ Model successfully quantized to ONNX format!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights", default="data/models/best.pt", help="Path to best.pt weights"
    )
    args = parser.parse_args()

    quantize(args.weights)


if __name__ == "__main__":
    main()
