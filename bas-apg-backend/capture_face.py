import cv2
import os

def capture_face():
    # Use camera 0 (HP cam) first, fallback to 1
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
        
    biometrics_dir = os.path.join(os.path.dirname(__file__), 'biometrics')
    os.makedirs(biometrics_dir, exist_ok=True)
        
    print(f"Opening webcam... Press 'c' to capture, or 'q' to quit.")
    print("Take multiple photos from different angles (left, right, up, down).")
    
    count = 1
    # Check existing files to avoid overwriting
    while os.path.exists(os.path.join(biometrics_dir, f"authorized_user_{count}.jpg")):
        count += 1
        
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Draw a face guide
        h, w = frame.shape[:2]
        center_x, center_y = w//2, h//2
        cv2.rectangle(frame, (center_x - 150, center_y - 200), (center_x + 150, center_y + 200), (0, 255, 0), 2)
        cv2.putText(frame, "Align face in box and press 'C' to capture", (center_x - 200, center_y - 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Captured: {count - 1}", (center_x - 70, center_y + 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        cv2.imshow("Multi-Angle Face Capture", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            filepath = os.path.join(biometrics_dir, f"authorized_user_{count}.jpg")
            cv2.imwrite(filepath, frame)
            print(f"✅ Captured face {count} and saved to {filepath}!")
            
            # Briefly flash the screen white to indicate capture
            flash = frame.copy()
            flash[:] = (255, 255, 255)
            cv2.imshow("Multi-Angle Face Capture", flash)
            cv2.waitKey(100)
            
            count += 1
        elif key == ord('q'):
            print(f"\nDone. Captured {count - 1} photos total.\n")
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_face()
