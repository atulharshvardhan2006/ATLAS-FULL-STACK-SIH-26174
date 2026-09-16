import cv2
import os

os.makedirs("captured_frames", exist_ok=True)
cam_index = 0
cap = cv2.VideoCapture(cam_index)

print("="*50)
print("📸 CAMERA CAPTURE TOOL STARTED")
print("="*50)
print(f"Currently using Camera Index: {cam_index}")
print("-> If you see the WRONG camera, press 'c' to switch cameras!")
print("-> Press SPACEBAR to take a picture of the object.")
print("-> Press 'q' to quit.")
print("="*50)
print("NOTE: If you don't see the window, check behind your IDE or look for the Python icon in your dock!\n")

count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print(f"Warning: Camera {cam_index} not responding. Trying to switch...")
        key = ord('c')
    else:
        cv2.imshow("Atlas Frame Capture - Press 'c' to switch cams", frame)
        key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break
    elif key == ord('c'):
        # Cycle camera
        cap.release()
        cv2.destroyAllWindows()
        cam_index = (cam_index + 1) % 3
        print(f"Switching to Camera Index: {cam_index}...")
        cap = cv2.VideoCapture(cam_index)
    elif key == 32:  # Spacebar
        filename = f"captured_frames/frame_{count}.jpg"
        cv2.imwrite(filename, frame)
        print(f"✅ Saved {filename}")
        count += 1

cap.release()
cv2.destroyAllWindows()
