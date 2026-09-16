"""
BAS-APG — Space Conditions Augmentation (Adversarial)

Simulates extreme microgravity and orbital lighting conditions:
- Zero atmospheric scattering (hard, pitch-black shadows)
- Orbital sunrise/sunset lens flares
- Harsh specular reflection on metallic tools

Retrain your YOLO model on this augmented dataset to prove robustness.
"""

import argparse
import glob
import os

import albumentations as A
import cv2
import numpy as np


def add_specular_reflection(image, **kwargs):
    """Simulate stark white reflection on metallic surfaces."""
    h, w = image.shape[:2]
    result = image.copy()

    # Generate 1 to 3 random reflection blobs
    num_blobs = np.random.randint(1, 4)
    for _ in range(num_blobs):
        cx = np.random.randint(0, w)
        cy = np.random.randint(0, h)
        radius = np.random.randint(10, 40)

        # Create a radial gradient (white center, fading out)
        y, x = np.ogrid[-cy : h - cy, -cx : w - cx]
        mask = x * x + y * y <= radius * radius

        if mask.any():
            dist = np.sqrt(x * x + y * y)[mask]
            intensity = 1.0 - (dist / radius)
            intensity = intensity**2  # Hard falloff

            # Apply additive white light
            for c in range(3):
                channel = result[:, :, c]
                channel_mask = channel[mask]
                # Add intensity, clip to 255
                channel[mask] = np.clip(
                    channel_mask + (intensity * 255), 0, 255
                ).astype(np.uint8)

    return result


def get_adversarial_pipeline():
    """Returns the Albumentations pipeline for Space Conditions."""
    return A.Compose(
        [
            # 1. Extreme Contrast (Zero-Scattering Shadows)
            A.RandomBrightnessContrast(
                brightness_limit=0.3,
                contrast_limit=(0.5, 1.5),  # Extreme contrast forces hard shadows
                p=0.8,
            ),
            # 2. Specular Reflection (Custom)
            A.Lambda(name="SpecularReflection", image=add_specular_reflection, p=0.5),
            # 3. Lens Flare (Simulating Orbital Sunrise)
            # Using RandomSunFlare which adds sun flares
            A.RandomSunFlare(
                flare_roi=(0, 0, 1, 0.5),  # Top half of image
                angle_lower=0,
                angle_upper=1,
                num_flare_circles_lower=1,
                num_flare_circles_upper=5,
                src_radius=200,
                src_color=(255, 255, 255),
                p=0.4,
            ),
            # 4. Sensor noise (Cosmic ray hits)
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
            # 5. Microgravity Rotation (Any angle)
            A.SafeRotate(limit=180, p=1.0),
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="data/images/train", help="Input image directory"
    )
    parser.add_argument(
        "--output", default="data/images/train_space", help="Output directory"
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    pipeline = get_adversarial_pipeline()

    images = glob.glob(os.path.join(args.input, "*.jpg"))
    if not images:
        print(f"No images found in {args.input}")
        return

    print(f"Applying Space Conditions to {len(images)} images...")

    for idx, img_path in enumerate(images):
        img = cv2.imread(img_path)
        if img is None:
            continue

        # Convert to RGB for Albumentations
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Apply pipeline
        augmented = pipeline(image=img_rgb)
        aug_img = augmented["image"]

        # Convert back to BGR
        aug_img_bgr = cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR)

        out_path = os.path.join(args.output, os.path.basename(img_path))
        cv2.imwrite(out_path, aug_img_bgr)

        if idx % 10 == 0:
            print(f"Processed {idx}/{len(images)}")

    print(
        "Done! Retrain YOLO on this folder to guarantee robustness against ISS lighting."
    )


if __name__ == "__main__":
    main()
