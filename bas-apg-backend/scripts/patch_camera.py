import os

filepath = "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/core/engine.py"

with open(filepath, 'r') as f:
    content = f.read()

# Replace hardcoded camera index 0 with 1 for the external HP w300 webcam
content = content.replace("cv2.VideoCapture(0)", "cv2.VideoCapture(1)")

with open(filepath, 'w') as f:
    f.write(content)
print("SUCCESS: Camera index updated to 1 for external webcam.")
