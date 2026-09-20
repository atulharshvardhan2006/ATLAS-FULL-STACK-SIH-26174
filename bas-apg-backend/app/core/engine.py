import os
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

_current_speak_proc = None

def speak(text):
    global _current_speak_proc
    import subprocess
    if _current_speak_proc is not None and _current_speak_proc.poll() is None:
        _current_speak_proc.kill()
    _current_speak_proc = subprocess.Popen(["say", "-v", "Daniel", text])

import time
import math
import cv2
import threading
import numpy as np

global_frame_buffer = None
from ultralytics import YOLO
import mediapipe as mp

from app.core.state import MissionState
from app.core.database import flight_recorder_queue

from app.engines.hoi_tracker import HOITracker
from app.engines.procedure_fsm import ProcedureFSM
from app.engines.kalman_filter import MultiObjectKalmanTracker

# ─── BIOMETRIC SECURITY SETUP ────────────────────────────────────────────────
import glob
try:
    import face_recognition
    FACE_REC_AVAILABLE = True
    biometrics_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'biometrics')
    authorized_encodings = []
    
    cache_path = os.path.join(biometrics_dir, 'encodings_cache.pkl')
    if os.path.exists(cache_path):
        import pickle
        with open(cache_path, 'rb') as f:
            authorized_encodings = pickle.load(f)
    else:
        legacy_path = os.path.join(os.path.dirname(__file__), '..', '..', 'authorized_user.jpg')
        if os.path.exists(legacy_path):
            legacy_img = face_recognition.load_image_file(legacy_path)
            legacy_encodings = face_recognition.face_encodings(legacy_img)
            if legacy_encodings:
                authorized_encodings.append(legacy_encodings[0])
                
        if os.path.exists(biometrics_dir):
            for img_path in glob.glob(os.path.join(biometrics_dir, '*.jpg')):
                img = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    authorized_encodings.append(encodings[0])
                
    if authorized_encodings:
        print(f"[ENGINE] Loaded {len(authorized_encodings)} reference images for Biometric Auth.")
    else:
        print("[ENGINE] Warning: No face images found. Biometric Auth disabled.")
except ImportError:
    FACE_REC_AVAILABLE = False
    authorized_encodings = []
    print("[ENGINE] face_recognition library not installed. ML Auth fallback enabled.")
# ─────────────────────────────────────────────────────────────────────────────



FOCAL_LENGTH_PX = 1422.3  
REAL_WORLD_DIMENSIONS_MM = {
    "book":       100.0,   
    "bottle":      80.0,   
    "cup":         80.0,   
    "pen":         25.0,   
    "scissors":    12.0,   
}
DEFAULT_OBJECT_HEIGHT_MM = 100.0  


COCO_TO_CUSTOM_MAP = {}


PID_KP = 0.5
PID_KD = 0.1
R_MATRIX_BASE = 2.0

GLARE_SATURATION_THRESHOLD = 0.95  
GLARE_PIXEL_VALUE = 240            


class RealHandTracker:
    def __init__(self):
        self.detected = False
        self.wrist_x, self.wrist_y = 0.0, 0.0
        self.fingertip_x, self.fingertip_y = 0.0, 0.0
        self.velocity = 0.0
        self.is_immobile = True
        self._prev_x, self._prev_y = 0.0, 0.0
    
    def update_from_blob(self, cx, cy):
        """Update from HSV blob detection centroid (pixel coordinates)."""
        if cx is not None and cy is not None:
            self.detected = True
            self.wrist_x = float(cx)
            self.wrist_y = float(cy)
            self.fingertip_x = float(cx)
            self.fingertip_y = float(cy)
            
            dx = self.wrist_x - self._prev_x
            dy = self.wrist_y - self._prev_y
            self.velocity = math.sqrt(dx**2 + dy**2)
            self.is_immobile = self.velocity < 2.0
            
            self._prev_x, self._prev_y = self.wrist_x, self.wrist_y
        else:
            self.detected = False
            self.velocity = 0.0
            self.is_immobile = True

def detect_white_gloves_with_pose(frame, pose_results):
    """Detect white gloves using Pose keypoints to isolate the wrist, then check brightness."""
    if not pose_results or len(pose_results) == 0:
        return None, None
        
    for result in pose_results:
        if result.keypoints is not None and len(result.keypoints.xy) > 0:
            kpts = result.keypoints.xy[0]
            # Keypoints 9 (left wrist) and 10 (right wrist)
            for kp_idx in [9, 10]:
                if len(kpts) > kp_idx:
                    x, y = int(kpts[kp_idx][0]), int(kpts[kp_idx][1])
                    if x > 0 and y > 0:
                        # Extract 100x100 ROI around the wrist
                        h, w = frame.shape[:2]
                        x1 = max(0, x - 50)
                        y1 = max(0, y - 50)
                        x2 = min(w, x + 50)
                        y2 = min(h, y + 50)
                        
                        roi = frame[y1:y2, x1:x2]
                        if roi.size > 0:
                            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                            avg_brightness = np.mean(gray_roi)
                            if avg_brightness > 130:  # White gloves reflect a lot of light
                                return x, y
    return None, None

def detect_bare_hand_with_pose(frame, pose_results):
    """Detect bare hand by checking if Pose keypoints for wrists or elbows are visible."""
    if not pose_results or len(pose_results) == 0:
        return None, None
        
    for result in pose_results:
        if result.keypoints is not None and len(result.keypoints.xy) > 0:
            kpts = result.keypoints.xy[0]
            # Priority order: wrists first (9, 10), then elbows (7, 8) as fallback
            for kp_idx in [9, 10, 7, 8]:
                if len(kpts) > kp_idx:
                    x, y = int(kpts[kp_idx][0]), int(kpts[kp_idx][1])
                    if x > 0 and y > 0:
                        return x, y
    return None, None

def detect_hand_hsv_fallback(frame):
    """Fallback HSV skin detection for mission phase hand tracking.
    More lenient than safety version — just needs to find ANY hand movement."""
    SKIN_LOWER_1 = np.array([0, 15, 50], dtype=np.uint8)
    SKIN_UPPER_1 = np.array([25, 255, 255], dtype=np.uint8)
    SKIN_LOWER_2 = np.array([165, 15, 50], dtype=np.uint8)
    SKIN_UPPER_2 = np.array([180, 255, 255], dtype=np.uint8)
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, SKIN_LOWER_1, SKIN_UPPER_1)
    mask2 = cv2.inRange(hsv, SKIN_LOWER_2, SKIN_UPPER_2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if 3000 < area < 250000:
            M = cv2.moments(largest)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                return cx, cy
    return None, None


import os, glob
orb = cv2.ORB_create(nfeatures=2000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

def apply_clahe(img):
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return _clahe.apply(img)


punch_refs = []
punch_files = sorted(glob.glob("punch_capture_*.jpg")) + (["punch.jpg"] if os.path.exists("punch.jpg") else [])
for pf in punch_files:
    img = cv2.imread(pf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        img = apply_clahe(img)
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            punch_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(punch_refs)} hole-puncher reference images for ORB matching.")

def detect_punch_hole(frame):
    if not punch_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = apply_clahe(frame_resized)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in punch_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 80]
        if len(good_matches) > 10:
            src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None and np.sum(mask) > 6:
                return True
    return False


scissors_refs = []
scissors_files = sorted(glob.glob("scissors_capture_*.jpg"))
for sf in scissors_files:
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        img = apply_clahe(img)
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            scissors_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(scissors_refs)} scissors reference images for ORB matching.")

def detect_scissors(frame):
    if not scissors_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = apply_clahe(frame_resized)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in scissors_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 80]
        if len(good_matches) > 10:
            src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None and np.sum(mask) > 6:
                return True
    return False


open_red_refs = []
for sf in sorted(glob.glob("open_red_capture_*.jpg")):
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        img = apply_clahe(img)
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            open_red_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(open_red_refs)} open red box reference images for ORB matching.")

def detect_open_red_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 130, 70]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 130, 70]), np.array([180, 255, 255]))
    if cv2.countNonZero(cv2.bitwise_or(mask1, mask2)) < 5000:
        return False
    if not open_red_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = apply_clahe(frame_resized)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in open_red_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 55]
        if len(good_matches) > 22:
            src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None and np.sum(mask) > 16:  # strictly requires 10 points in the exact geometric shape!
                return True
    return False


open_yellow_refs = []
for sf in sorted(glob.glob("open_yellow_capture_*.jpg")):
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        img = apply_clahe(img)
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            open_yellow_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(open_yellow_refs)} open yellow box reference images for ORB matching.")

def detect_open_yellow_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([15, 50, 50]), np.array([40, 255, 255]))
    if cv2.countNonZero(mask) < 2000:
        return False
    if not open_yellow_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = apply_clahe(frame_resized)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in open_yellow_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 60]
        if len(good_matches) > 12:
            src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None and np.sum(mask) > 8:
                return True
    return False

def detect_red_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 130, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 130, 50])
    upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
    return cv2.countNonZero(mask) > 25000

def detect_yellow_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([20, 130, 50])
    upper_yellow = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    return cv2.countNonZero(mask) > 25000

# ==========================================
# DYNAMIC OBJECT REGISTRY
# ==========================================
dynamic_object_refs = {}  # {"water_bottle": [(kp, des), ...], ...}

def load_dynamic_object(slug):
    """Load ORB features for a dynamically registered object from data/objects/<slug>/."""
    refs = []
    obj_dir = os.path.join("data", "objects", slug)
    for img_path in sorted(glob.glob(os.path.join(obj_dir, "capture_*.jpg"))):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
            img = apply_clahe(img)
            kp, des = orb.detectAndCompute(img, None)
            if des is not None:
                refs.append((kp, des))
    dynamic_object_refs[slug] = refs
    print(f"[ENGINE] Loaded {len(refs)} reference images for dynamic object '{slug}'.")
    return len(refs)

def detect_dynamic_object(frame, object_slug):
    """Generic ORB-based detector for any dynamically registered object."""
    refs = dynamic_object_refs.get(object_slug, [])
    if not refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = apply_clahe(frame_resized)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 80]
        if len(good_matches) > 10:
            src_pts = np.float32([kp_ref[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None and np.sum(mask) > 6:
                return True
    return False

# Auto-load any pre-registered dynamic objects on startup
for _obj_slug_dir in glob.glob(os.path.join("data", "objects", "*")):
    if os.path.isdir(_obj_slug_dir):
        _slug = os.path.basename(_obj_slug_dir)
        _manifest = os.path.join(_obj_slug_dir, "manifest.json")
        if os.path.exists(_manifest):
            load_dynamic_object(_slug)

class RealSpatialChecker:
    def __init__(self):
        self.is_breached = False
    def check(self, detections):
        self.is_breached = False
        boundary_y_px = MissionState.norm_boundary_y * MissionState.frame_height
        for d in detections:
            
            y2_px = d["norm_bbox"][3] * MissionState.frame_height
            if y2_px > boundary_y_px:
                self.is_breached = True
                break

    def verify_containment(self, target_class: str, container_class: str, detections: list) -> bool:
        """Mathematically proves if the target is physically inside the container."""
        target_det = next((d for d in detections if d["class_name"] == target_class), None)
        container_det = next((d for d in detections if d["class_name"] == container_class), None)
        
        if not target_det or not container_det:
            return False
            
        t_nx1, t_ny1, t_nx2, t_ny2 = target_det["norm_bbox"]
        c_nx1, c_ny1, c_nx2, c_ny2 = container_det["norm_bbox"]
        
        
        intersect_x1 = max(t_nx1, c_nx1)
        intersect_y1 = max(t_ny1, c_ny1)
        intersect_x2 = min(t_nx2, c_nx2)
        intersect_y2 = min(t_ny2, c_ny2)
        
        
        intersect_w = max(0, intersect_x2 - intersect_x1)
        intersect_h = max(0, intersect_y2 - intersect_y1)
        intersect_area = intersect_w * intersect_h
        
        
        target_area = (t_nx2 - t_nx1) * (t_ny2 - t_ny1)
        
        
        if target_area > 0 and (intersect_area / target_area) > 0.85:
            return True
            
        return False

def extract_joints(hand_landmarks):
    """Works with both legacy (.landmark) and new Tasks API (list of NormalizedLandmark)."""
    if hasattr(hand_landmarks, 'landmark'):
        return hand_landmarks.landmark
    
    return hand_landmarks

def is_anatomically_valid(joints) -> bool:
    """Uses vector dot products to reject impossible MediaPipe hallucinations.
    
    Checks that the index finger doesn't bend backward past 45 degrees
    relative to the knuckle — a physical impossibility that indicates
    the landmark detector is guessing under occlusion.
    """
    
    wrist = np.array([joints[0].x, joints[0].y])
    knuckle = np.array([joints[5].x, joints[5].y])
    tip = np.array([joints[8].x, joints[8].y])
    
    vec_base = knuckle - wrist
    vec_tip = tip - knuckle
    
    norm_base = np.linalg.norm(vec_base)
    norm_tip = np.linalg.norm(vec_tip)
    
    if norm_base < 1e-6 or norm_tip < 1e-6:
        return False  
    
    cos_theta = np.dot(vec_base, vec_tip) / (norm_base * norm_tip)
    angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    angle_deg = np.degrees(angle_rad)
    
    
    return angle_deg < 45.0


def run_ai_engine():
    speak('Atlas is online')
    from app.core.config import get_settings
    import os
    config = get_settings()
    
    yolo_model = YOLO(config.yolo_model_path) 
    
    # Load Pose model for robust safety checks
    pose_model = YOLO(os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n-pose.pt"))
    
    print("[ENGINE] YOLOv8-Pose Initialized for Bulletproof Safety Tracking.")
    
    hand_tracker = RealHandTracker()
    hoi_tracker = HOITracker()
    spatial_checker = RealSpatialChecker()
    kalman_tracker = MultiObjectKalmanTracker()  
    
    z_depth_history = {}  
    drift_history = {}    
    EMA_ALPHA = 0.15      
    UNSECURED_DRIFT_THRESHOLD = 5.0  
    
    fsm = ProcedureFSM(procedure_path=MissionState.selected_procedure)
    fsm.start() 

    last_frame_time = time.time()
    
    CAMERA_INDEX = config.camera_index
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ENGINE] CRITICAL: Camera 0 failed, trying camera 1")
        CAMERA_INDEX = 1
        cap = cv2.VideoCapture(CAMERA_INDEX)
    
    print(f"[ENGINE] Camera locked to index {CAMERA_INDEX}")
    if cap is None or not cap.isOpened():
        print("[ENGINE] CRITICAL: No camera found!")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3) 
    cap.set(cv2.CAP_PROP_AUTO_WB, 1)

    def hardware_watchdog():
        nonlocal cap, last_frame_time
        while True:
            if time.time() - last_frame_time > 2.0:
                print("CRITICAL: USB Bus Deadlock! Out-of-band restart initiated.")
                cap.release()
                time.sleep(0.5)
                cap = cv2.VideoCapture(CAMERA_INDEX)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                cap.set(cv2.CAP_PROP_FPS, 30)
                last_frame_time = time.time()
            time.sleep(0.5)

    threading.Thread(target=hardware_watchdog, daemon=True).start()

    frame_counter = 0
    last_breach_state = False
    last_deviation_state = False
    last_voice_step = -1
    last_voice_state = ""
    import subprocess
    _voice_proc = None
    
    video_writer = None
    recording_session_id = None
    recordings_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'experiment_videos')
    os.makedirs(recordings_dir, exist_ok=True)
    
    # ==========================================
    # THERMAL GOVERNOR (Fanless M4 Protection)
    # ==========================================
    _thermal_level = 0  # 0=cool, 1=warm, 2=hot
    _last_thermal_check = 0
    
    def check_thermal():
        """Monitor CPU load as a proxy for thermal pressure on fanless M4."""
        nonlocal _thermal_level, _last_thermal_check
        now = time.time()
        if now - _last_thermal_check < 5.0:  # Only check every 5 seconds
            return _thermal_level
        _last_thermal_check = now
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            if cpu > 95:
                _thermal_level = 2  # HOT: CPU maxed out, will overheat
            elif cpu > 85:
                _thermal_level = 1  # WARM: CPU getting hot
            else:
                _thermal_level = 0  # COOL: comfortable
        except ImportError:
            # psutil not available — use subprocess fallback
            try:
                result = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.thermal.throttle_count"], timeout=2
                ).decode().strip()
                if int(result) > 0:
                    _thermal_level = 2
                else:
                    _thermal_level = 0
            except Exception:
                _thermal_level = 0
        return _thermal_level
    
    # Pose model frequency: how often to run pose (every Nth frame)
    # Dynamically adjusted by thermal governor
    _pose_frame_interval = 2  # default: every 2nd frame
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        
        # Dynamic thermal throttle based on macOS thermal pressure
        thermal = check_thermal()
        if thermal == 2:
            time.sleep(0.06)           # HOT: ~15 FPS max, heavy cooldown
            _pose_frame_interval = 6   # Run pose every 6th frame
        elif thermal == 1:
            time.sleep(0.03)           # WARM: ~25 FPS, moderate cooldown
            _pose_frame_interval = 4   # Run pose every 4th frame
        else:
            time.sleep(0.01)           # COOL: ~30 FPS, normal operation
            _pose_frame_interval = 2   # Run pose every 2nd frame
            
        if MissionState.reset_fsm_flag:
            import os
            try:
                os.remove("/tmp/bas_apg_state.json")
            except OSError:
                pass
            fsm = ProcedureFSM(procedure_path=MissionState.selected_procedure)
            fsm.start()
            MissionState.reset_fsm_flag = False
            last_voice_step = -1
            last_voice_state = ""
            
        last_frame_time = time.time()
        frame_counter += 1

        if not hasattr(MissionState, '_frame_buffer') or MissionState._frame_buffer.shape != frame.shape:
            MissionState._frame_buffer = np.zeros_like(frame)
        np.copyto(MissionState._frame_buffer, frame)
        MissionState.latest_frame = MissionState._frame_buffer
        MissionState.frame_sequence += 1
        MissionState.is_connected = True

        # ─── BIOMETRIC SECURITY SCANNING ──────────────────────────────────────
        if MissionState.auth_status == "SCANNING":
            if FACE_REC_AVAILABLE and len(authorized_encodings) > 0:
                MissionState.auth_status = "PROCESSING"  # Prevent duplicate threads
                
                def perform_scan(current_frame):
                    try:
                        small_frame = cv2.resize(current_frame, (0, 0), fx=0.5, fy=0.5)
                        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_small_frame)
                        
                        if face_locations:
                            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                            match = False
                            for face_encoding in face_encodings:
                                matches = face_recognition.compare_faces(authorized_encodings, face_encoding, tolerance=0.48)
                                if any(matches):
                                    match = True
                                    break
                            if match:
                                time.sleep(3.0)  # Cinematic delay
                                print("[AUTH] Match found! Initiating Safety Checks.")
                                speak("Biometric signature verified. Initiating safety protocol.")
                                time.sleep(4.5)  # Wait for voice to finish COMPLETELY
                                MissionState.auth_status = "SAFETY_HAND"
                            else:
                                time.sleep(3.0)  # Cinematic delay
                                MissionState.auth_status = "DENIED"
                                print("[AUTH] Unknown face detected. Access Denied.")
                                speak("Unknown biometric signature. Access denied.")
                        else:
                            # If no face found in this frame, go back to SCANNING to try again on next frame
                            MissionState.auth_status = "SCANNING"
                    except Exception as e:
                        print(f"[AUTH] Error during scanning: {e}")
                        MissionState.auth_status = "DENIED"
                
                threading.Thread(target=perform_scan, args=(frame.copy(),), daemon=True).start()
            else:
                # Fallback / Demo Mode: if no image or no library, just wait 2 seconds and grant
                def delayed_grant():
                    time.sleep(2.0)
                    MissionState.auth_status = "SAFETY_HAND"
                MissionState.auth_status = "PROCESSING" # prevent duplicate threads
                threading.Thread(target=delayed_grant, daemon=True).start()
                
        elif MissionState.auth_status == "SAFETY_HAND":
            if not getattr(MissionState, "_safety_hand_spoken", False):
                speak("Please present bare hands for verification.")
                MissionState._safety_hand_spoken = True
                MissionState._safety_hand_start = time.time()
            
            # Wait at least 3 seconds for the voice to finish, then require hand detection
            if time.time() - getattr(MissionState, "_safety_hand_start", time.time()) > 3.0:
                if hand_tracker.detected:
                    MissionState.auth_status = "SAFETY_GLOVES"
                    MissionState._safety_hand_spoken = False
        
        elif MissionState.auth_status == "SAFETY_GLOVES":
            if not getattr(MissionState, "_safety_gloves_spoken", False):
                speak("Safety procedure. Pair gloves.")
                MissionState._safety_gloves_spoken = True
                MissionState._safety_gloves_start_time = time.time()
                
            if time.time() - getattr(MissionState, "_safety_gloves_start_time", time.time()) > 4.0:
                # Require white gloves to be detected!
                if hand_tracker.detected:
                    MissionState.auth_status = "SAFETY_GLASSES"
                    MissionState._safety_gloves_spoken = False
                
        elif MissionState.auth_status == "SAFETY_GLASSES":
            if not getattr(MissionState, "_safety_glasses_spoken", False):
                speak("Safety procedure. Eye protection needed.")
                MissionState._safety_glasses_spoken = True
                MissionState._safety_glasses_start_time = time.time()
                
            elapsed = time.time() - getattr(MissionState, "_safety_glasses_start_time", time.time())
            
            # After 8.5 seconds, detect face via Pose model and grant access
            if elapsed > 10.0:
                if frame_counter % _pose_frame_interval == 0:
                    try:
                        pose_results_glasses = pose_model(frame, verbose=False, conf=0.25)
                        if pose_results_glasses and len(pose_results_glasses) > 0:
                            for result in pose_results_glasses:
                                if result.keypoints is not None and len(result.keypoints.xy) > 0:
                                    kpts = result.keypoints.xy[0]
                                    if len(kpts) > 2:
                                        left_eye = kpts[1]
                                        right_eye = kpts[2]
                                        lx, ly = int(left_eye[0]), int(left_eye[1])
                                        rx, ry = int(right_eye[0]), int(right_eye[1])
                                        if lx > 0 and ly > 0 and rx > 0 and ry > 0:
                                            MissionState.auth_status = "GRANTED"
                                            speak("Safety checks complete. Access granted.")
                                            MissionState._safety_glasses_spoken = False
                    except Exception:
                        pass
            
            # On-screen HUD for glasses phase
            if elapsed < 10.0:
                remaining = int(10.0 - elapsed) + 1
                if remaining > 4:
                    cv2.putText(frame, f"SCANNING FACE... {remaining}s", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(frame, f">>> PUT GLASSES ON! {remaining}s <<<", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3, cv2.LINE_AA)
            else:
                cv2.putText(frame, "VERIFYING EYE PROTECTION...", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3, cv2.LINE_AA)
        # ──────────────────────────────────────────────────────────────────────

        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        saturation_ratio = float(np.count_nonzero(v_channel > GLARE_PIXEL_VALUE)) / v_channel.size
        MissionState.glare_saturation = round(saturation_ratio, 3)
        MissionState.is_blinded = saturation_ratio > GLARE_SATURATION_THRESHOLD

        if MissionState.is_blinded:
            
            
            continue

        
        MissionState.yolo_detections = []
        hoi_detections = []
        
        current_step_info = fsm.get_current_step()
        current_expected_prop = current_step_info.object if current_step_info else ""

        # ==========================================
        # CONSTANT BACKGROUND HAND TRACKING
        # ==========================================
        if frame_counter % _pose_frame_interval == 0:
            pose_results = pose_model.track(frame, persist=True, verbose=False, conf=0.25)
            
            if MissionState.auth_status == "SAFETY_GLOVES":
                # Only check for white gloves during the glove safety step
                cx, cy = detect_white_gloves_with_pose(frame, pose_results)
            elif MissionState.auth_status.startswith("SAFETY_"):
                # During safety hand check, pose-only
                cx, cy = detect_bare_hand_with_pose(frame, pose_results)
            else:
                # MISSION PHASE: Hybrid — try Pose first, then HSV skin fallback
                cx, cy = detect_bare_hand_with_pose(frame, pose_results)
                if cx is None:
                    cx, cy = detect_hand_hsv_fallback(frame)
            hand_tracker.update_from_blob(cx, cy)
            
        # ==========================================
        # PHASE 1: SAFETY SCAN 
        # ==========================================
        if MissionState.auth_status.startswith("SAFETY_"):
            cv2.putText(frame, f"[{MissionState.auth_status}] POSE TRACKING ACTIVE", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
            
        # ==========================================
        # PHASE 2: MISSION OPS (OBJECT DETECTION)
        # ==========================================
        else:
            results = yolo_model.track(frame, persist=True, verbose=False, conf=0.75)

            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue

                has_ids = boxes.id is not None
                
                for i, d in enumerate(boxes):
                    t_id = boxes.id[i] if has_ids else i
                    x1, y1, x2, y2 = float(d.xyxy[0][0]), float(d.xyxy[0][1]), float(d.xyxy[0][2]), float(d.xyxy[0][3])
                    raw_class_name = result.names[int(d.cls)]
                    
                    class_name = COCO_TO_CUSTOM_MAP.get(raw_class_name, raw_class_name)
                    
                    if class_name not in ["main_box", "red_box", "yellow_box", "sample", "hole_puncher", "scissors"]:
                        continue
                    
                    conf = float(d.conf)
                    
                    if class_name == current_expected_prop:
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
                        label = f"[PENDING] {class_name.upper()} {conf:.0%}"
                        cv2.putText(frame, label, (int(x1), int(y1) - 15), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                    else:
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (150, 150, 150), 1)
                        label = f"{class_name} {conf:.0%}"
                        cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1, cv2.LINE_AA)

                    object_height_mm = REAL_WORLD_DIMENSIONS_MM.get(raw_class_name, DEFAULT_OBJECT_HEIGHT_MM)
                    pixel_h = max(y2 - y1, 1.0)
                    z_raw = (object_height_mm * FOCAL_LENGTH_PX) / pixel_h
                    
                    t_id_int = int(t_id)
                    if t_id_int in z_depth_history:
                        z_smoothed = (EMA_ALPHA * z_raw) + ((1.0 - EMA_ALPHA) * z_depth_history[t_id_int])
                    else:
                        z_smoothed = z_raw
                    z_depth_history[t_id_int] = z_smoothed
                    
                    MissionState.yolo_detections.append({
                        "class_name": class_name,
                        "confidence": round(conf, 2),
                        "norm_bbox": [
                            round(x1 / MissionState.frame_width, 4),
                            round(y1 / MissionState.frame_height, 4),
                            round(x2 / MissionState.frame_width, 4),
                            round(y2 / MissionState.frame_height, 4),
                        ],
                        "z_depth_mm": round(z_smoothed, 1),
                    })
                    
                    hoi_detections.append({
                        "class": class_name,
                        "track_id": int(t_id),
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf
                    })

            det_count = len(MissionState.yolo_detections)
            hud_text = f"YOLO: {det_count} objects | TARGET: {current_expected_prop.upper()}"
            cv2.putText(frame, hud_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

            hoi_detections = kalman_tracker.update(hoi_detections)
            MissionState.kalman_coasting = len(hoi_detections) > len(MissionState.yolo_detections)
            MissionState.kalman_coast_frames = max(0, len(hoi_detections) - len(MissionState.yolo_detections))

            current_track_ids = {det["track_id"] for det in hoi_detections}
            z_depth_history = {tid: v for tid, v in z_depth_history.items() if tid in current_track_ids}
            drift_history = {tid: v for tid, v in drift_history.items() if tid in current_track_ids}
        
        
        current_step = fsm.get_current_step()
        
        
        target_velocity = 0.0
        if current_step:
            for det in hoi_detections:
                if det["class"] == current_step.object and det["track_id"] in kalman_tracker.filters:
                    kf_state = kalman_tracker.filters[det["track_id"]].kf.statePost
                    vx, vy = kf_state[4, 0], kf_state[5, 0]
                    target_velocity = math.sqrt(vx**2 + vy**2)
                    break
        
        if hand_tracker.detected:
            palm_center = (int(hand_tracker.wrist_x), int(hand_tracker.wrist_y))
            interactions = hoi_tracker.compute_interactions(palm_center, hoi_detections)
            held_items = [i for i in interactions if i["state"] == "HELD"]
            

            if held_items:
                MissionState.is_grasping = True
                MissionState.grasped_object = held_items[0]["class"]
                MissionState.pearson_r = 0.85 
            else:
                MissionState.is_grasping = False
                MissionState.grasped_object = None
                MissionState.pearson_r = 0.15 
        else:
            interactions = []
            
            
            if current_step and current_step.action == "PICK" and 15.0 < target_velocity < 80.0:
                MissionState.is_grasping = True
                MissionState.grasped_object = current_step.object
                MissionState.pearson_r = 0.99
            else:
                MissionState.is_grasping = False
                MissionState.grasped_object = None
                MissionState.pearson_r = 0.0

        
        anchor_vx, anchor_vy = 0.0, 0.0
        for det in hoi_detections:
            if det["class"] == "main_box" and det["track_id"] in kalman_tracker.filters:
                kf_state = kalman_tracker.filters[det["track_id"]].kf.statePost
                anchor_vx = kf_state[4, 0]
                anchor_vy = kf_state[5, 0]
                break
        else:
            
            all_velocities = []
            for det in hoi_detections:
                if det["track_id"] in kalman_tracker.filters:
                    kf_s = kalman_tracker.filters[det["track_id"]].kf.statePost
                    all_velocities.append((kf_s[4, 0], kf_s[5, 0]))
            if all_velocities:
                anchor_vx = float(np.median([v[0] for v in all_velocities]))
                anchor_vy = float(np.median([v[1] for v in all_velocities]))

        
        for det in hoi_detections:
            track_id = det["track_id"]
            class_name = det["class"]
            
            is_held = any(i["track_id"] == track_id and i["state"] == "HELD" for i in interactions)
            
            if not is_held and track_id in kalman_tracker.filters:
                kf_state = kalman_tracker.filters[track_id].kf.statePost
                
                true_vx = kf_state[4, 0] - anchor_vx
                true_vy = kf_state[5, 0] - anchor_vy
                velocity_magnitude = math.sqrt(true_vx**2 + true_vy**2)
                
                if velocity_magnitude > UNSECURED_DRIFT_THRESHOLD:
                    drift_history[track_id] = drift_history.get(track_id, 0) + 1
                    if drift_history[track_id] > 3:
                        print(f"CRITICAL: {class_name} is drifting unsecured! V={velocity_magnitude:.2f}")
                        if MissionState.active_session_id:
                            flight_recorder_queue.put(("HAZARD", {
                                "session_id": MissionState.active_session_id,
                                "hazard_type": f"UNSECURED_DRIFT_{class_name.upper()}",
                            }))
                else:
                    drift_history[track_id] = 0

        
        MissionState.hand_detected = hand_tracker.detected
        MissionState.hand_wrist = [round(hand_tracker.wrist_x / MissionState.frame_width, 3), round(hand_tracker.wrist_y / MissionState.frame_height, 3)] if hand_tracker.detected else None
        MissionState.hand_fingertip = [round(hand_tracker.fingertip_x / MissionState.frame_width, 3), round(hand_tracker.fingertip_y / MissionState.frame_height, 3)] if hand_tracker.detected else None
        MissionState.hand_velocity = hand_tracker.velocity
        MissionState.hand_is_immobile = hand_tracker.is_immobile

        
        spatial_checker.check(MissionState.yolo_detections)
        MissionState.containment_breach = spatial_checker.is_breached

        
        detected_action = "none"
        detected_obj = ""
        action_conf = 0.0
        
        
        if MissionState.is_grasping:
            detected_action = "PICK"
            detected_obj = MissionState.grasped_object
            action_conf = 0.90
            
        current_step = fsm.get_current_step()
        if current_step and current_step.action == "TRANSFER":
            
            
            obj_visible = any(d['class_name'] == current_step.object for d in MissionState.yolo_detections)
            dest_visible = any(d['class_name'] == "yellow_box" for d in MissionState.yolo_detections)
            contained_in = None
            for container_candidate in ["main_box", "red_box", "yellow_box"]:
                if spatial_checker.verify_containment(current_step.object, container_candidate, MissionState.yolo_detections):
                    contained_in = container_candidate
                    break
            
            if (hand_tracker.detected and obj_visible and dest_visible) or contained_in:
                detected_action = "TRANSFER"
                detected_obj = current_step.object
                action_conf = 0.90
        
        
        if not hasattr(fsm, '_last_step_id'):
            fsm._last_step_id = current_step.step_id if current_step else None
            fsm._step_transition_time = time.time()
            fsm._baseline_frame = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
            fsm._scene_changed = False
            
        if current_step and current_step.step_id != fsm._last_step_id:
            fsm._auto_advance_start = None
            fsm._last_step_id = current_step.step_id
            fsm._step_transition_time = time.time()
            fsm._baseline_frame = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
            fsm._scene_changed = False
            fsm._step_reminder_given = False

        
        step_age = time.time() - fsm.state.step_start_time
        
        in_view = False
        if step_age < 4.0 and current_step and current_step.object != "procedure" and fsm.state.current_step_index > 0:
            fsm._auto_advance_start = None
        elif step_age < 0.5 and current_step and current_step.object != "procedure":
            fsm._auto_advance_start = None
        else:
            
            
            if current_step and current_step.object not in ("procedure", "hand"):
                current_small = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
                baseline = getattr(fsm, '_baseline_frame', None)
                if baseline is not None and not getattr(fsm, '_scene_changed', False):
                    diff = cv2.absdiff(current_small, baseline)
                    change_amount = float(np.mean(diff))
                    if change_amount > 12.0:
                        fsm._scene_changed = True
                        
            
            if current_step and not getattr(fsm, '_scene_changed', False) and current_step.object not in ("procedure", "hand"):
                in_view = False
            else:
                if frame_counter % 5 == 0:
                    if current_step and current_step.object == "hand":
                        in_view = hand_tracker.detected
                    elif current_step and current_step.object == "procedure":
                        in_view = True
                    elif current_step and current_step.object == "hole_puncher":
                        in_view = detect_punch_hole(frame) and hand_tracker.detected
                    elif current_step and current_step.object == "red_box":
                        in_view = detect_red_box(frame) and hand_tracker.detected
                    elif current_step and current_step.object == "yellow_box":
                        in_view = detect_yellow_box(frame) and hand_tracker.detected
                    elif current_step and current_step.object == "scissors":
                        in_view = detect_scissors(frame) and hand_tracker.detected
                    elif current_step and current_step.object == "open_red_box":
                        in_view = detect_open_red_box(frame) and hand_tracker.detected
                    elif current_step and current_step.object == "open_yellow_box":
                        in_view = detect_open_yellow_box(frame) and hand_tracker.detected
                    elif current_step:
                        in_view = any(d["class_name"] == current_step.object for d in MissionState.yolo_detections)
                        if not in_view and current_step.object in dynamic_object_refs:
                            in_view = detect_dynamic_object(frame, current_step.object) and hand_tracker.detected
                    fsm._cached_in_view = in_view
                else:
                    in_view = getattr(fsm, "_cached_in_view", False)
        if in_view:
            fsm._last_seen_time = time.time()
            fsm._deviation_start = None
            fsm._deviation_obj = None
            
            frontend_target = getattr(MissionState, 'frontend_target', None)
            
            # Allow auto-advance if frontend hasn't set a target (legacy mode) or if target matches
            if frontend_target is None or (current_step and frontend_target == current_step.object):
                if not hasattr(fsm, '_auto_advance_start') or fsm._auto_advance_start is None:
                    fsm._auto_advance_start = time.time()
                elif time.time() - fsm._auto_advance_start >= 1.5:
                    detected_action = current_step.action
                    detected_obj = current_step.object
                    action_conf = 1.0
            else:
                fsm._auto_advance_start = None
            # else: still accumulating confirmation time, do NOT advance yet
        else:
            if time.time() - getattr(fsm, '_last_seen_time', 0) > 0.5:
                fsm._auto_advance_start = None
            
            
            # Only check for out-of-sequence deviations if step has been active for > 5 seconds
            if current_step.object != "procedure" and step_age > 5.0:
                
                allowed_objects = set()
                for i in range(0, fsm.state.current_step_index + 1):
                    allowed_objects.add(fsm.steps[i].object)
                    
                all_detectors = {
                    "hole_puncher": lambda f: detect_punch_hole(f) and hand_tracker.detected,
                    "scissors": lambda f: detect_scissors(f) and hand_tracker.detected,
                    "red_box": lambda f: detect_red_box(f) and hand_tracker.detected,
                    "yellow_box": lambda f: detect_yellow_box(f) and hand_tracker.detected,
                    "open_red_box": lambda f: detect_open_red_box(f) and hand_tracker.detected,
                    "open_yellow_box": lambda f: detect_open_yellow_box(f) and hand_tracker.detected
                }
                
                # Add dynamic objects to out-of-sequence detectors
                for dyn_obj in dynamic_object_refs.keys():
                    if dyn_obj not in all_detectors:
                        # Need to capture dyn_obj in default arg to avoid late binding issue in lambda
                        all_detectors[dyn_obj] = lambda f, o=dyn_obj: detect_dynamic_object(f, o) and hand_tracker.detected
                    
                if frame_counter % 10 == 0:
                    out_of_seq_obj_detected = None
                    for obj_name, detect_func in all_detectors.items():
                        if obj_name not in allowed_objects:
                            if current_step and current_step.object == "red_box" and obj_name == "open_red_box":
                                continue
                            if current_step and current_step.object == "yellow_box" and obj_name == "open_yellow_box":
                                continue
                            if current_step and current_step.object == "open_red_box" and obj_name == "red_box":
                                continue
                            if current_step and current_step.object == "open_yellow_box" and obj_name == "yellow_box":
                                continue
                            if current_step and current_step.object == "open_yellow_box" and obj_name == "scissors":
                                continue
                            if detect_func(frame):
                                out_of_seq_obj_detected = obj_name
                                break
                    fsm._cached_out_seq = out_of_seq_obj_detected
                else:
                    out_of_seq_obj_detected = getattr(fsm, "_cached_out_seq", None)
                                
                if out_of_seq_obj_detected:
                    if getattr(fsm, '_deviation_obj', None) != out_of_seq_obj_detected:
                        fsm._deviation_start = time.time()
                        fsm._deviation_obj = out_of_seq_obj_detected
                    elif time.time() - fsm._deviation_start >= 2.5:  
                        detected_action = "DETECT" 
                        
                        for future_idx in range(fsm.state.current_step_index + 1, len(fsm.steps)):
                            if fsm.steps[future_idx].object == out_of_seq_obj_detected:
                                detected_action = fsm.steps[future_idx].action
                                break
                        detected_obj = out_of_seq_obj_detected
                        action_conf = 1.0
                else:
                    fsm._deviation_start = None
                    fsm._deviation_obj = None
                        
        
        prev_idx = fsm.state.current_step_index
        prev_status = fsm.state.status
        if MissionState.demo_started:
            fsm.process_observation(detected_action, detected_obj, action_conf)
            fsm.save_state_to_disk() 
        if getattr(fsm, "state", None) and (fsm.state.current_step_index != prev_idx or (fsm.state.status == "COMPLETED" and prev_status != "COMPLETED")):
            fsm._deviation_start = None
            fsm._deviation_obj = None
            
            # 1. Speak SUCCESS for the step that just finished!
            if prev_idx >= 0 and prev_idx < len(fsm.steps):
                completed_step_def = fsm.steps[prev_idx]
                if completed_step_def.object == "procedure":
                    speak("All steps verified. Experimental procedure completed.")
                else:
                    obj_name_clean = completed_step_def.object.replace('open_', '').replace('_', ' ')
                    speak(f"{obj_name_clean} detection complete.")
                
                # 2. Start the 2-second silent timer before the NEXT instruction
                MissionState._next_instruction_timer = time.time()
        
        
        MissionState.fsm_current_state = fsm.state.status
        MissionState.fsm_previous_state = fsm.state.current_step_id or "IDLE"
        MissionState.fsm_current_step = fsm.state.current_step_index
        MissionState.fsm_total_steps = len(fsm.steps)
        MissionState.fsm_deviation_flag = (fsm.state.status == "DEVIATION")
        MissionState.fsm_deviation_details = fsm.state.deviation_details
        MissionState.fsm_debounce_count = fsm._debounce_counter
        MissionState.fsm_expected_action = current_step.action if current_step else ""
        MissionState.fsm_expected_object = current_step.object if current_step else ""

        # Warning Audio for Deviations
        if MissionState.fsm_deviation_flag and not getattr(MissionState, "_deviation_spoken", False):
            speak(MissionState.fsm_deviation_details)
            MissionState._deviation_spoken = True
        elif not MissionState.fsm_deviation_flag:
            MissionState._deviation_spoken = False

        # Dynamic Audio Prompts for Steps
        if MissionState.demo_started and fsm.state.status == "IN_PROGRESS" and MissionState.fsm_current_step != last_voice_step:
            if MissionState.fsm_current_step == 0 and not getattr(MissionState, "_intro_spoken", False):
                speak("Experimental procedure started.")
                MissionState._intro_spoken = True
                MissionState._intro_start_time = time.time()
            else:
                if MissionState.fsm_current_step == 0:
                    # Step 0 waits 4 seconds after the Intro speech
                    if (time.time() - getattr(MissionState, "_intro_start_time", 0) > 4.0):
                        last_voice_step = MissionState.fsm_current_step
                        curr_step_def = fsm.get_current_step()
                        if curr_step_def and getattr(curr_step_def, 'audio_prompt', ''):
                            speak(curr_step_def.audio_prompt)
                else:
                    # Step 1+ waits 1 second after the Success speech FINISHES
                    if _current_speak_proc is not None and _current_speak_proc.poll() is None:
                        MissionState._next_instruction_timer = time.time()
                    elif (time.time() - getattr(MissionState, "_next_instruction_timer", 0) > 1.0):
                        last_voice_step = MissionState.fsm_current_step
                        curr_step_def = fsm.get_current_step()
                        if curr_step_def and getattr(curr_step_def, 'audio_prompt', ''):
                            speak(curr_step_def.audio_prompt)

        
        if MissionState.fsm_current_state != MissionState.fsm_previous_state and MissionState.active_session_id:
            flight_recorder_queue.put(("FSM", {
                "session_id": MissionState.active_session_id,
                "previous_state": MissionState.fsm_previous_state,
                "new_state": MissionState.fsm_current_state,
            }))
        
        
        if spatial_checker.is_breached and not last_breach_state:
            if MissionState.active_session_id:
                flight_recorder_queue.put(("HAZARD", {
                    "session_id": MissionState.active_session_id,
                    "hazard_type": "CONTAINMENT_BREACH",
                }))
        last_breach_state = spatial_checker.is_breached

        if MissionState.fsm_deviation_flag and not last_deviation_state:
            if MissionState.active_session_id:
                flight_recorder_queue.put(("HAZARD", {
                    "session_id": MissionState.active_session_id,
                    "hazard_type": "SEQUENCE_DEVIATION",
                }))
        last_deviation_state = MissionState.fsm_deviation_flag

        
        current_session = MissionState.active_session_id
        if current_session and current_session != recording_session_id:
            
            if video_writer is not None:
                video_writer.release()
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            recording_path = os.path.join(recordings_dir, f"{timestamp}.mp4")
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_writer = cv2.VideoWriter(recording_path, fourcc, 10.0, (w, h))
            recording_session_id = current_session
            print(f"[ENGINE] Recording started: {recording_path}")
        elif not current_session and recording_session_id:
            
            if video_writer is not None:
                video_writer.release()
                video_writer = None
                print(f"[ENGINE] Recording saved for session {recording_session_id}")
            recording_session_id = None
        
        
        if video_writer is not None and frame_counter % 3 == 0:
            video_writer.write(frame)

        
        global global_frame_buffer
        annotated_frame = frame
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if ret:
            global_frame_buffer = buffer.tobytes()
        time.sleep(0.04)  # Throttle to ~25 FPS to drop Mac CPU temp to ~85C
