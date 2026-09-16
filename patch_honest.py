import os

path = '/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-backend/app/core/engine.py'
with open(path, 'r') as f: lines = f.readlines()

new_lines = []
in_hand_tracker = False

for line in lines:
    # 1. Fix HandTracker so it resets to False if no skin is seen
    if "def update_from_skin(self, cx, cy):" in line:
        new_lines.append(line)
        new_lines.append("        if cx is None or cy is None:\n")
        new_lines.append("            self.detected = False\n")
        new_lines.append("            return\n")
        continue

    # 2. Fix the ORB reference images so they don't match the background of the user's room!
    # Whenever a reference image is loaded via imread for ORB, we MUST crop the center to isolate the object!
    if "img = cv2.imread(pf, cv2.IMREAD_GRAYSCALE)" in line or "img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)" in line:
        new_lines.append(line)
        new_lines.append("        if img is not None:\n")
        new_lines.append("            H, W = img.shape\n")
        new_lines.append("            # Crop the center 40% of the image where the object is held, dropping the room background\n")
        new_lines.append("            img = img[int(H*0.3):int(H*0.7), int(W*0.3):int(W*0.7)]\n")
        continue

    new_lines.append(line)

with open(path, 'w') as f:
    f.write("".join(new_lines))
print("Patched engine.py for real honest detections!")
