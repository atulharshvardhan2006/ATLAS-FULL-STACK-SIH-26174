import cv2
import os
import glob
import numpy as np

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

def auto_annotate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(script_dir, "../captured_frames")
    label_dir = os.path.join(script_dir, "data/dataset/labels/train")
    out_img_dir = os.path.join(script_dir, "data/dataset/images/train")
    
    os.makedirs(label_dir, exist_ok=True)
    os.makedirs(out_img_dir, exist_ok=True)
    
    images = glob.glob(f"{img_dir}/*.jpg")
    print(f"Starting auto-annotation on {len(images)} images...")
    
    success_count = 0
    for img_path in images:
        frame = cv2.imread(img_path)
        if frame is None: continue
        H, W = frame.shape[:2]
        
        detected_class = None
        bbox = None
        
        # 1. Red Box
        bbox = get_hsv_bbox(frame, np.array([0, 120, 70]), np.array([10, 255, 255]), np.array([170, 120, 70]), np.array([180, 255, 255]))
        if bbox:
            detected_class = "red_box"
        else:
            # 2. Yellow Box
            bbox = get_hsv_bbox(frame, np.array([15, 100, 100]), np.array([35, 255, 255]))
            if bbox:
                detected_class = "yellow_box"
                
        # For scissors/punch_hole, auto-annotating with ORB is too unreliable without good reference images.
        # We will just label the color boxes automatically and tell the user to use labelImg for the rest.
            
        if detected_class and bbox:
            x, y, w, h = bbox
            x_center = (x + w/2) / W
            y_center = (y + h/2) / H
            norm_w = w / W
            norm_h = h / H
            
            class_id = CLASSES[detected_class]
            base_name = os.path.basename(img_path)
            txt_name = base_name.replace(".jpg", ".txt")
            
            with open(os.path.join(label_dir, txt_name), "w") as f:
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}\n")
            
            cv2.imwrite(os.path.join(out_img_dir, base_name), frame)
            success_count += 1
            
    print(f"✅ Auto-annotated {success_count} / {len(images)} images (mostly Red/Yellow boxes).")
    print(f"You only need to manually annotate the remaining {len(images) - success_count} images (like scissors) in labelImg!")

if __name__ == "__main__":
    auto_annotate()
