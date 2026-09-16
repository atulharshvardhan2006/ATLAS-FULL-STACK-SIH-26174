import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

# Suppress YOLO verbosity for the output
logging.getLogger("ultralytics").setLevel(logging.WARNING)

def main():
    try:
        from app.core.config import get_settings
        from ultralytics import YOLO
    except ImportError as e:
        print(f"Error importing modules: {e}")
        sys.exit(1)

    # Parse engine.py to avoid missing dependency imports
    import re
    import os
    engine_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'core', 'engine.py')
    with open(engine_path, 'r') as f:
        content = f.read()
    match = re.search(r'FOCAL_LENGTH_PX\s*=\s*([0-9.]+)', content)
    FOCAL_LENGTH_PX = float(match.group(1)) if match else None

    config = get_settings()

    # 1. Print the active FOCAL_LENGTH_PX to the terminal.
    print(FOCAL_LENGTH_PX)
    
    # 2. Print the active yolo_model_path.
    print(config.yolo_model_path)

    # 3. Attempt to initialize the YOLO model using that exact path
    try:
        # Loading the weights
        model = YOLO(config.yolo_model_path)
        print("SYSTEM GO")
    except Exception as e:
        print(f"SYSTEM NO-GO: {e}")

if __name__ == "__main__":
    main()
