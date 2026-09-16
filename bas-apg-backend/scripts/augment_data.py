"""
BAS-APG — Microgravity Data Augmentation Pipeline

Simulates zero-G conditions by augmenting training images with:
  - 360° rotation (objects float freely, no fixed "up" vector)
  - Brightness/contrast variation (ISS lighting changes)
  - Flips (remove directional bias)
  - Noise (camera sensor variation)
  - Partial occlusion (astronaut hand blocking view)

Usage:
    conda activate bas_apg_env
    python scripts/augment_data.py --input data/raw --output data/augmented --copies 5
"""

import argparse
import glob
import os

import albumentations as A
import cv2
from albumentations import BboxParams


def create_augmentation_pipeline() -> A.Compose:
    """Create the microgravity simulation augmentation pipeline."""
    return A.Compose(
        [
            # PRIMARY: Simulate zero-G rotation — objects at ANY angle
            A.SafeRotate(
                limit=180,  # Full 360° rotation (±180°)
                p=1.0,  # 100% chance per image for aggressive augmentation
                border_mode=cv2.BORDER_CONSTANT,
                fill=0,  # Black fill for rotated edges
            ),
            # ISS lighting variations
            A.RandomBrightnessContrast(
                brightness_limit=0.3,
                contrast_limit=0.3,
                p=1.0,
            ),
            # Remove directional bias
            A.HorizontalFlip(p=0.3),
            A.VerticalFlip(p=0.3),
            # Camera sensor noise
            A.GaussNoise(var_limit=(10, 50), p=0.3),
            # Partial occlusion (hand blocking view)
            A.CoarseDropout(
                max_holes=3,
                max_height=50,
                max_width=50,
                p=0.2,
            ),
        ],
        bbox_params=BboxParams(
            format="yolo",  # YOLO format: class x_center y_center w h
            label_fields=["class_labels"],
            min_visibility=0.3,  # Drop boxes that become <30% visible
        ),
    )


def load_yolo_labels(label_path: str) -> tuple[list[list[float]], list[int]]:
    """Load YOLO-format bounding box labels from a .txt file.

    Returns:
        (bboxes, class_labels) where bboxes are [x_center, y_center, w, h]
    """
    bboxes = []
    class_labels = []

    if not os.path.exists(label_path):
        return bboxes, class_labels

    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_labels.append(int(parts[0]))
                bboxes.append([float(x) for x in parts[1:5]])

    return bboxes, class_labels


def save_yolo_labels(label_path: str, bboxes: list, class_labels: list):
    """Save bounding boxes in YOLO format."""
    with open(label_path, "w") as f:
        for cls, bbox in zip(class_labels, bboxes):
            coords = " ".join(f"{v:.6f}" for v in bbox)
            f.write(f"{cls} {coords}\n")


def augment_dataset(
    input_dir: str,
    output_dir: str,
    augmentations_per_image: int = 5,
):
    """Augment entire dataset with microgravity transforms.

    Args:
        input_dir: Directory containing images/ and labels/ subdirs.
        output_dir: Output directory for augmented images/ and labels/.
        augmentations_per_image: Number of augmented copies per image.
    """
    os.makedirs(f"{output_dir}/images", exist_ok=True)
    os.makedirs(f"{output_dir}/labels", exist_ok=True)

    transform = create_augmentation_pipeline()

    # Find all images
    image_patterns = [
        f"{input_dir}/images/*.jpg",
        f"{input_dir}/images/*.jpeg",
        f"{input_dir}/images/*.png",
    ]
    images = []
    for pattern in image_patterns:
        images.extend(glob.glob(pattern))

    if not images:
        print(f"ERROR: No images found in {input_dir}/images/")
        print("Expected structure: input_dir/images/*.jpg + input_dir/labels/*.txt")
        return

    print(f"Found {len(images)} images")
    print(f"Generating {augmentations_per_image} augmented copies each")
    print(f"Total output: {len(images) * augmentations_per_image} images")
    print()

    total_generated = 0

    for img_path in images:
        image = cv2.imread(img_path)
        if image is None:
            print(f"  WARNING: Could not read {img_path}, skipping")
            continue

        # Load corresponding labels
        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(input_dir, "labels", f"{base}.txt")
        bboxes, class_labels = load_yolo_labels(label_path)

        # Generate augmented copies
        for i in range(augmentations_per_image):
            try:
                if bboxes:
                    result = transform(
                        image=image,
                        bboxes=bboxes,
                        class_labels=class_labels,
                    )
                else:
                    # No labels — just augment the image
                    result = {
                        "image": transform(image=image, bboxes=[], class_labels=[])[
                            "image"
                        ]
                    }
                    result["bboxes"] = []
                    result["class_labels"] = []

                aug_img_path = f"{output_dir}/images/{base}_aug_{i}.jpg"
                aug_lbl_path = f"{output_dir}/labels/{base}_aug_{i}.txt"

                cv2.imwrite(aug_img_path, result["image"])
                save_yolo_labels(aug_lbl_path, result["bboxes"], result["class_labels"])
                total_generated += 1

            except Exception as e:
                print(f"  WARNING: Augmentation failed for {base}_aug_{i}: {e}")

    print(f"\n✅ Augmentation complete!")
    print(f"   Generated: {total_generated} images")
    print(f"   Output: {output_dir}/images/ and {output_dir}/labels/")


def main():
    parser = argparse.ArgumentParser(
        description="BAS-APG Microgravity Data Augmentation"
    )
    parser.add_argument(
        "--input",
        default="data/raw",
        help="Input directory with images/ and labels/ subdirs",
    )
    parser.add_argument(
        "--output",
        default="data/augmented",
        help="Output directory for augmented data",
    )
    parser.add_argument(
        "--copies",
        type=int,
        default=5,
        help="Number of augmented copies per image (default: 5)",
    )

    args = parser.parse_args()
    augment_dataset(args.input, args.output, args.copies)


if __name__ == "__main__":
    main()
