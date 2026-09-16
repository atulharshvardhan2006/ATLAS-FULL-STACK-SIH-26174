import os
import re

filepath = "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-frontend/src/pages/Mission.tsx"

with open(filepath, 'r') as f:
    content = f.read()

pattern = r'(<div className="absolute inset-0 z-20 pointer-events-none">)'

replacement = """        <img 
          src="http://localhost:8000/video_feed" 
          alt="Live Optics" 
          className="absolute inset-0 w-full h-full object-cover z-0 opacity-80"
        />
        \\1"""

new_content, count = re.subn(pattern, replacement, content)

if count > 0:
    with open(filepath, 'w') as f:
        f.write(new_content)
    print("SUCCESS: Webcam video_feed injected into OpticalTrunk.")
else:
    print("FAILED: Could not find target string in Mission.tsx.")
