# BAS-APG — YOLO Model Training Plan

## Objective
Train a custom YOLOv8n model to detect the 5 physical objects used in BAS experiments with >90% mAP@0.5 on Apple Silicon M4.

---

## 1. Class Definitions

| Class ID | Class Name   | Physical Object                     | Min Samples |
|----------|-------------|--------------------------------------|-------------|
| 0        | main_box    | White/grey primary containment unit  | 150         |
| 1        | red_box     | Red-labeled secondary container      | 150         |
| 2        | yellow_box  | Yellow-labeled hazardous container   | 150         |
| 3        | sample      | Small specimen / regolith simulant   | 200         |
| 4        | tweezers    | Titanium/steel tweezers/forceps      | 200         |

**Total minimum raw images: ~850**
After augmentation (8x multiplier from existing scripts): **~6,800 training images**

---

## 2. Image Capture Protocol

### Camera Setup
- **Device:** HP w300 USB Webcam (same as deployment camera)
- **Resolution:** 1920×1080 (match `cap.set` in engine.py)
- **Format:** JPEG, saved via `cv2.imwrite()`

### Capture Script
Use `scripts/capture_analog.py` to save frames. Target **30 images per object per condition**.

### Conditions Matrix

| Condition           | Variations                                      | Purpose                    |
|--------------------|-------------------------------------------------|----------------------------|
| **Lighting**       | Overhead fluorescent, desk lamp, window natural  | Robustness to venue lights |
| **Angle**          | Top-down (45°), frontal (0°), oblique (30°)      | Viewpoint invariance       |
| **Scale/Distance** | Near (30cm), mid (60cm), far (100cm)             | Depth estimation accuracy  |
| **Occlusion**      | Partially hidden by hand, stacked objects        | Real-world clutter         |
| **Background**     | White table, dark bench, cluttered desk          | Venue adaptation           |

### Per-Object Shot List

For each of the 5 objects:
1. **Isolated** — object alone, 3 lighting × 3 angles = 9 shots
2. **In-hand** — held by operator, 3 lighting × 2 angles = 6 shots
3. **In-context** — on workbench with other objects, 3 backgrounds × 3 distances = 9 shots
4. **Edge cases** — partially occluded, tilted, upside-down = 6 shots

**Total per object: ~30 raw images**

---

## 3. Annotation

### Tool
Use [Roboflow](https://roboflow.com) or [LabelImg](https://github.com/HumanSignal/labelImg) for bounding box annotation.

### Format
YOLO format (one `.txt` per image):
```
<class_id> <x_center> <y_center> <width> <height>
```
All values normalized to [0, 1].

### Rules
- Box must tightly enclose the entire visible object
- If >50% occluded, do NOT annotate (skip)
- Tweezers: annotate the full length including handles
- Sample: annotate even if very small (<20px) — these are hard positives

---

## 4. Augmentation Pipeline

Use the existing scripts in `scripts/`:

### `augment_data.py`
- Random rotation (±15°)
- Horizontal flip
- Brightness/contrast jitter
- Gaussian noise
- Random crop (80-100% of image)

### `augment_space_conditions.py`
- Simulated microgravity lighting gradients
- Lens distortion (barrel/pincushion)
- Color temperature shift (warm/cool)
- Motion blur (1-3px kernel)

**Expected multiplier: 8× raw dataset**

---

## 5. Dataset Split

| Split       | Ratio | Purpose              |
|-------------|-------|----------------------|
| Training    | 70%   | Model learning       |
| Validation  | 20%   | Hyperparameter tuning|
| Test        | 10%   | Final mAP evaluation |

### Directory Structure
```
data/
├── dataset/
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── labels/
│       ├── train/
│       ├── val/
│       └── test/
└── dataset.yaml
```

### `dataset.yaml`
```yaml
path: data/dataset
train: images/train
val: images/val
test: images/test

names:
  0: main_box
  1: red_box
  2: yellow_box
  3: sample
  4: tweezers
```

---

## 6. Training Configuration

Use `scripts/train_yolo.py` with these parameters:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # Nano for edge deployment
results = model.train(
    data="data/dataset.yaml",
    epochs=100,
    imgsz=640,
    batch=16,            # M4 16GB can handle this
    device="mps",        # Apple Metal Performance Shaders
    workers=4,
    patience=20,         # Early stopping
    lr0=0.01,
    lrf=0.001,
    augment=True,
    mosaic=1.0,
    mixup=0.1,
    copy_paste=0.1,
)
```

### Expected Training Time on M4
- ~100 epochs × 6,800 images ÷ batch 16 = **~2-3 hours** on MPS

---

## 7. Validation Targets

| Metric        | Target  | Acceptable |
|---------------|---------|------------|
| mAP@0.5       | >0.90   | >0.85      |
| mAP@0.5:0.95  | >0.70   | >0.60      |
| Inference (ms)| <15ms   | <25ms      |
| FPS on M4     | >30     | >25        |

### Per-Class Minimums
- `main_box`: AP >0.92 (large, easy)
- `red_box`: AP >0.90 (color-distinct)
- `yellow_box`: AP >0.90 (color-distinct)
- `sample`: AP >0.80 (small, hardest class)
- `tweezers`: AP >0.85 (thin, elongated)

---

## 8. Deployment Checklist

- [ ] Capture raw images (all 5 classes × all conditions)
- [ ] Annotate in YOLO format
- [ ] Run `augment_data.py` and `augment_space_conditions.py`
- [ ] Split into train/val/test
- [ ] Create `dataset.yaml`
- [ ] Train with `train_yolo.py` on M4 (MPS backend)
- [ ] Validate mAP targets met
- [ ] Export best weights: `best.pt`
- [ ] Update `engine.py`: `YOLO("runs/detect/train/weights/best.pt")`
- [ ] Re-run inference to confirm 30 FPS maintained
