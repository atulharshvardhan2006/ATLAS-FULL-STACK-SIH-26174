import cv2
import time

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("=" * 50)
print("  HOLE PUNCHER IMAGE CAPTURE")
print("=" * 50)
print("  Press 'C' to capture an image")
print("  Press 'Q' to quit")
print("=" * 50)

count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    display = frame.copy()
    cv2.putText(display, "Press C to CAPTURE | Q to QUIT", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(display, f"Images captured: {count}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    
    cv2.imshow("Hole Puncher Capture", display)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c') or key == ord('C'):
        count += 1
        filename = f"punch_capture_{count}.jpg"
        cv2.imwrite(filename, frame)
        # Also overwrite the main punch.jpg used by the engine
        cv2.imwrite("punch.jpg", frame)
        print(f"  [SAVED] {filename} + punch.jpg updated!")
    elif key == ord('q') or key == ord('Q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\nDone! Captured {count} image(s). punch.jpg has been updated.")
