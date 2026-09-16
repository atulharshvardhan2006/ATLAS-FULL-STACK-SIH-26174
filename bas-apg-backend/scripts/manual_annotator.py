import cv2
import os
import glob

# Our Custom Classes for YOLO
# 0: main_box
# 1: red_box
# 2: yellow_box
# 3: sample
# 4: hole_puncher
# 5: scissors

CLASS_MAP = {
    ord('1'): (1, "red_box"),
    ord('2'): (2, "yellow_box"),
    ord('4'): (4, "hole_puncher"),
    ord('5'): (5, "scissors")
}

VIDEO_DIR = "data/raw/videos"
IMAGE_DIR = "data/raw/images"
LABEL_DIR = "data/raw/labels"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(LABEL_DIR, exist_ok=True)

def create_yolo_label(img_shape, bbox, class_id):
    ih, iw = img_shape[:2]
    x, y, w, h = bbox
    cx = (x + w/2) / iw
    cy = (y + h/2) / ih
    nw = w / iw
    nh = h / ih
    return f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"

def main():
    videos = glob.glob(f"{VIDEO_DIR}/*.mp4")
    if not videos:
        print(f"❌ No videos found in {VIDEO_DIR}!")
        return

    frame_count = 0
    
    print("\n" + "="*50)
    print("🚀 RAPID MANUAL ANNOTATOR")
    print("="*50)
    print("1. Drag a box around the object.")
    print("2. Press SPACE or ENTER to confirm the box.")
    print("3. Press a number key to label it:")
    print("   [1] -> red_box")
    print("   [2] -> yellow_box")
    print("   [4] -> hole_puncher")
    print("   [5] -> scissors")
    print("4. Press [s] to skip the frame.")
    print("5. Press [q] to quit early.")
    print("="*50 + "\n")

    for video_path in videos:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames < 10:
            step = 1
        else:
            step = total_frames // 10
            
        current_frame = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if current_frame % step == 0 and (current_frame // step) < 10:
                h, w = frame.shape[:2]
                if w > 1280:
                    scale = 1280 / w
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                window_name = f"Draw Box - Frame {frame_count}"
                bbox = cv2.selectROI(window_name, frame, False, False)
                
                if bbox[2] == 0 or bbox[3] == 0:
                    print("Skipped box drawing.")
                    cv2.destroyWindow(window_name)
                    current_frame += 1
                    continue
                    
                print("Press 1, 2, 4, or 5 to label (or 's' to skip).")
                key = cv2.waitKey(0) & 0xFF
                cv2.destroyWindow(window_name)
                
                if key == ord('q'):
                    print("Quitting...")
                    cap.release()
                    cv2.destroyAllWindows()
                    return
                elif key in CLASS_MAP:
                    class_id, class_name = CLASS_MAP[key]
                    
                    img_path = os.path.join(IMAGE_DIR, f"frame_{frame_count:04d}.jpg")
                    cv2.imwrite(img_path, frame)
                    
                    txt_path = os.path.join(LABEL_DIR, f"frame_{frame_count:04d}.txt")
                    yolo_str = create_yolo_label(frame.shape, bbox, class_id)
                    with open(txt_path, "w") as f:
                        f.write(yolo_str)
                        
                    print(f"✅ Saved {class_name} ({img_path})")
                    frame_count += 1
                else:
                    print("Frame skipped.")
                    
            current_frame += 1
            
        cap.release()
        
    cv2.destroyAllWindows()
    print(f"\n🎉 Done! Annotated {frame_count} frames total.")

if __name__ == "__main__":
    main()
