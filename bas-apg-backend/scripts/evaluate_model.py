"""
BAS-APG — Model Evaluation Script

Runs inference on a validation or test set, generates a Confusion Matrix,
calculates F1-Scores, and helps tune NMS thresholds.

Usage:
    python scripts/evaluate_model.py --weights data/models/best.pt --data data/dataset.yaml --split val
"""

import argparse
import os

from ultralytics import YOLO


def evaluate(weights_path: str, data_path: str, split: str = "val"):
    if not os.path.exists(weights_path):
        print(f"ERROR: Model weights not found at {weights_path}")
        return

    print("=" * 60)
    print(" BAS-APG — Model Evaluation")
    print(f" Weights: {weights_path}")
    print(f" Dataset: {data_path}")
    print("=" * 60)

    print("Loading model...")
    model = YOLO(weights_path, task="detect")

    print(f"\nRunning validation on '{split}' split...")
    # Evaluate the model on the validation set
    # Using conf=0.25 (typical starting point) and iou=0.45 (NMS threshold)
    metrics = model.val(
        data=data_path,
        split=split,
        conf=0.25,
        iou=0.45,
        plots=True,  # Generates confusion matrix and F1-curves
        save_json=True,
        project="data/eval",
        name="bas_apg_eval",
        exist_ok=True,
    )

    print("\n✅ Evaluation Complete!")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    print(f"  mAP50:    {metrics.box.map50:.4f}")

    # Calculate F1-Score from precision and recall
    precision = metrics.box.mp
    recall = metrics.box.mr

    f1 = 0.0
    if (precision + recall) > 0:
        f1 = 2 * (precision * recall) / (precision + recall)

    print(f"  Mean Precision: {precision:.4f}")
    print(f"  Mean Recall:    {recall:.4f}")
    print(f"  Mean F1-Score:  {f1:.4f}")

    print("\nResults and plots (Confusion Matrix, F1-curve, PR-curve) saved to:")
    print(f"  {os.path.abspath('data/eval/bas_apg_eval')}")

    print("\n💡 NMS Tuning Advice:")
    print(
        "  - If False Positives are high (background detected as objects), INCREASE confidence threshold in config.py."
    )
    print(
        "  - If False Negatives are high (missing real objects), DECREASE confidence threshold in config.py."
    )
    print(
        "  - Review the Confusion Matrix in the eval folder to see edge-case performance (e.g., occluded tweezers)."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights", default="data/models/best.pt", help="Path to model weights"
    )
    parser.add_argument(
        "--data", default="data/dataset.yaml", help="Path to dataset.yaml"
    )
    parser.add_argument(
        "--split", default="val", help="Dataset split to evaluate (val or test)"
    )
    args = parser.parse_args()

    evaluate(args.weights, args.data, args.split)


if __name__ == "__main__":
    main()
