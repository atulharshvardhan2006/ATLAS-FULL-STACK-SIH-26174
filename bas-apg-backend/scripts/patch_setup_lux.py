import os
import re

filepath = "/Users/atulharshvardhan/Desktop/BAS-APG-Workspace/bas-apg-frontend/src/pages/Setup.tsx"

with open(filepath, 'r') as f:
    content = f.read()

# Remove setLux
content = content.replace("const [lux, setLux] = useState(450);", "const [lux] = useState(450);")

with open(filepath, 'w') as f:
    f.write(content)
