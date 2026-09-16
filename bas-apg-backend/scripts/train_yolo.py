"""
BAS-APG — YOLOv8 Microgravity Training Script

Trains a YOLOv8 Nano model on the augmented microgravity dataset.
Targeting Apple Silicon (M4 / MPS) for rapid local training.

Usage:
    conda activate bas_apg_env
    python scripts/train_yolo.py --epochs 50 --batch 16
"""

import argparse
import os

from ultralytics import YOLO


def train_model(epochs: int, batch_size: int, device: str = "mps"):
    """Train YOLOv8 on the dataset."""
    print("=" * 60)
    print("  BAS-APG — YOLOv8 Training Initialization")
    print("=" * 60)

    # Define dataset config
    abs_data_path = os.path.abspath("data")
    data_yaml_content = f"""
path: {abs_data_path}
train: augmented/images
val: augmented/images  # Using same for demo, should be split in prod
nc: 6
names:
  0: main_box
  1: red_box
  2: yellow_box
  3: sample
  4: hole_puncher
  5: scissors
"""
    os.makedirs("data", exist_ok=True)
    with open("data/dataset.yaml", "w") as f:
        f.write(data_yaml_content.strip())

    print("[TRAIN] Created dataset.yaml")

    # Load model
    print("[TRAIN] Loading YOLOv8n pre-trained model...")
    model = YOLO("yolov8n.pt")

    # Start training
    print(f"[TRAIN] Starting training for {epochs} epochs on device: {device}")
    model.train(
        data="data/dataset.yaml",
        epochs=epochs,
        imgsz=640,
        batch=batch_size,
        device=device,
        project="data/models",
        name="bas_apg_yolo",
        exist_ok=True,
        patience=10,  # Early stopping to monitor mAP50-95
    )

    print("\n✅ Training Complete!")
    print("Model saved to: data/models/bas_apg_yolo/weights/best.pt")

    # Copy best model to expected location (Ultralytics actually places it in runs/)
    os.system("mkdir -p data/models && cp runs/detect/data/models/bas_apg_yolo/weights/best.pt data/models/best.pt")
    print("Copied to: data/models/best.pt (Ready for inference)")


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 for BAS-APG")
    parser.add_argument(
        "--epochs", type=int, default=50, help="Number of training epochs"
    )
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument(
        "--device",
        type=str,
        default="mps",
        help="Device to use (mps for Mac, cpu, cuda)",
    )

    args = parser.parse_args()

    # Auto-fallback to cpu if mps is not available (though M4 supports it)
    try:
        import torch

        if args.device == "mps" and not torch.backends.mps.is_available():
            print("MPS not available, falling back to CPU")
            args.device = "cpu"
    except ImportError:
        pass

    train_model(args.epochs, args.batch, args.device)


if __name__ == "__main__":
    main()
