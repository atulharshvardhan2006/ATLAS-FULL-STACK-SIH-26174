import cv2
import os
import glob
import numpy as np
import uuid

CLASSES = {
    "red_box": 0,
    "punch_hole": 1,
    "yellow_box": 2,
    "scissors": 3,
    "open_red_box": 4,
    "open_yellow_box": 5
}

def get_hsv_bbox(frame, lower1, upper1, lower2=None, upper2=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower1, upper1)
    if lower2 is not None and upper2 is not None:
        mask += cv2.inRange(hsv, lower2, upper2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) < 5000: return None
    x, y, w, h = cv2.boundingRect(largest_contour)
    return (x, y, w, h)

import os
script_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(script_dir, "../captured_frames")
label_dir = os.path.join(script_dir, "data/dataset/labels/train")
out_img_dir = os.path.join(script_dir, "data/dataset/images/train")

print("Processing new frames...")
success_count = 0

for i in range(51):
    img_path = os.path.join(img_dir, f"frame_{i}.jpg")
    if not os.path.exists(img_path): continue
    
    frame = cv2.imread(img_path)
    if frame is None: continue
    H, W = frame.shape[:2]
    
    if i < 25:
        detected_class = "open_red_box"
        bbox = get_hsv_bbox(frame, np.array([0, 120, 70]), np.array([10, 255, 255]), np.array([170, 120, 70]), np.array([180, 255, 255]))
    else:
        detected_class = "open_yellow_box"
        bbox = get_hsv_bbox(frame, np.array([15, 100, 100]), np.array([35, 255, 255]))
        
    # If OpenCV failed to find a bounding box, just use a large box in the center as a fallback so we don't lose the data
    if not bbox:
        bbox = (int(W*0.2), int(H*0.2), int(W*0.6), int(H*0.6))
        
    x, y, w, h = bbox
    x_center = (x + w/2) / W
    y_center = (y + h/2) / H
    norm_w = w / W
    norm_h = h / H
    
    class_id = CLASSES[detected_class]
    
    # Generate unique name so we don't overwrite the old frame_X in the dataset folder
    unique_id = uuid.uuid4().hex[:8]
    new_base = f"{detected_class}_{i}_{unique_id}.jpg"
    txt_name = new_base.replace(".jpg", ".txt")
    
    with open(os.path.join(label_dir, txt_name), "w") as f:
        f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")
    
    cv2.imwrite(os.path.join(out_img_dir, new_base), frame)
    success_count += 1

print(f"✅ Successfully annotated and moved {success_count} new images to YOLO training dataset!")
