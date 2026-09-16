import cv2
import time
from ultralytics import YOLO

print("Loading model data/models/best.pt...")
try:
    model = YOLO("data/models/best.pt")
    print("Model classes mapping:", model.names)
except Exception as e:
    print("Failed to load model:", e)
    exit(1)

print("Opening camera...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Could not open any camera.")
    exit(1)

print("\n=======================================================")
print("!!! PLEASE HOLD YOUR PUNCH HOLE AND SCISSORS !!!")
print("!!!      IN FRONT OF THE CAMERA RIGHT NOW      !!!")
print("=======================================================\n")
for i in range(5, 0, -1):
    print(f"Capturing in {i} seconds...")
    time.sleep(1)

ret, frame = cap.read()
if ret:
    cv2.imwrite("debug_capture.jpg", frame)
    print("\n[+] Image successfully saved as debug_capture.jpg")
    
    # Run YOLO with very low confidence to see EVERYTHING it thinks might be there
    results = model(frame, verbose=False, conf=0.1)
    print("\n--- YOLO Detections (conf >= 0.1) ---")
    if results[0].boxes:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls_id]
            print(f"Detected: '{name}' (Confidence: {conf:.2f})")
    else:
        print("No objects detected by YOLO.")
else:
    print("Failed to read frame from camera.")
cap.release()
