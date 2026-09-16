import time
import math
import cv2
import threading
import numpy as np

global_frame_buffer = None
from ultralytics import YOLO
from app.core.state import MissionState
from app.core.database import flight_recorder_queue

from app.engines.hoi_tracker import HOITracker
from app.engines.procedure_fsm import ProcedureFSM
from app.engines.kalman_filter import MultiObjectKalmanTracker


SKIN_LOWER_1 = np.array([0, 30, 60], dtype=np.uint8)    
SKIN_UPPER_1 = np.array([20, 150, 255], dtype=np.uint8)
SKIN_LOWER_2 = np.array([160, 30, 60], dtype=np.uint8)   
SKIN_UPPER_2 = np.array([180, 150, 255], dtype=np.uint8)
SKIN_MIN_AREA = 5000  
SKIN_MAX_AREA = 350000 


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
    
    def update_from_skin(self, cx, cy):
        """Update from HSV skin detection centroid (pixel coordinates)."""
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

def detect_skin(frame):
    """Detect skin-colored regions using dual-range HSV thresholds.
    Returns (center_x, center_y) of the largest skin blob, or (None, None)."""
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
        if SKIN_MIN_AREA < area < SKIN_MAX_AREA:
            M = cv2.moments(largest)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                return cx, cy
    return None, None


import os, glob
orb = cv2.ORB_create(nfeatures=1000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


punch_refs = []
punch_files = sorted(glob.glob("punch_capture_*.jpg")) + (["punch.jpg"] if os.path.exists("punch.jpg") else [])
for pf in punch_files:
    img = cv2.imread(pf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            punch_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(punch_refs)} hole-puncher reference images for ORB matching.")

def detect_punch_hole(frame):
    if not punch_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in punch_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 55]
        if len(good_matches) > 12:  
            return True
    return False


scissors_refs = []
scissors_files = sorted(glob.glob("scissors_capture_*.jpg"))
for sf in scissors_files:
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            scissors_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(scissors_refs)} scissors reference images for ORB matching.")

def detect_scissors(frame):
    if not scissors_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in scissors_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 55]
        if len(good_matches) > 15:  
            return True
    return False


open_red_refs = []
for sf in sorted(glob.glob("open_red_capture_*.jpg")):
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            open_red_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(open_red_refs)} open red box reference images for ORB matching.")

def detect_open_red_box(frame):
    if not open_red_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in open_red_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 55]
        if len(good_matches) > 15:  
            return True
    return False


open_yellow_refs = []
for sf in sorted(glob.glob("open_yellow_capture_*.jpg")):
    img = cv2.imread(sf, cv2.IMREAD_GRAYSCALE)
    if img is not None:
        img = cv2.resize(img, (640, int(640 * img.shape[0] / img.shape[1])))
        kp, des = orb.detectAndCompute(img, None)
        if des is not None:
            open_yellow_refs.append((kp, des))
print(f"[ENGINE] Loaded {len(open_yellow_refs)} open yellow box reference images for ORB matching.")

def detect_open_yellow_box(frame):
    if not open_yellow_refs:
        return False
    frame_resized = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
    frame_gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
    kp_frame, des_frame = orb.detectAndCompute(frame_gray, None)
    if des_frame is None:
        return False
    for kp_ref, des_ref in open_yellow_refs:
        matches = bf.match(des_ref, des_frame)
        good_matches = [m for m in matches if m.distance < 55]
        if len(good_matches) > 15:  
            return True
    return False

def detect_red_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
    return cv2.countNonZero(mask) > 100000  

def detect_yellow_box(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_yellow = np.array([15, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    return cv2.countNonZero(mask) > 100000  

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
    from app.core.config import get_settings
    import os
    config = get_settings()
    
    yolo_model = YOLO(config.yolo_model_path) 
    
    print("[ENGINE] HSV Skin-Color Hand Detection initialized (no neural network needed).")
    
    hand_tracker = RealHandTracker()
    hoi_tracker = HOITracker()
    spatial_checker = RealSpatialChecker()
    kalman_tracker = MultiObjectKalmanTracker()  
    
    z_depth_history = {}  
    drift_history = {}    
    EMA_ALPHA = 0.15      
    UNSECURED_DRIFT_THRESHOLD = 5.0  
    
    fsm = ProcedureFSM(procedure_path="data/procedures/red_yellow_box_experiment.json")
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
    
    def speak(text):
        nonlocal _voice_proc
        if _voice_proc is not None:
            _voice_proc.terminate()
            _voice_proc.wait()
        _voice_proc = subprocess.Popen(["say", "-v", "Alex", text])
    
    
    video_writer = None
    recording_session_id = None
    recordings_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'experiment_videos')
    os.makedirs(recordings_dir, exist_ok=True)
    
    speak("ATLAS is online")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
            
        if MissionState.reset_fsm_flag:
            import os
            try:
                os.remove("/tmp/bas_apg_state.json")
            except OSError:
                pass
            fsm = ProcedureFSM(procedure_path="data/procedures/red_yellow_box_experiment.json")
            fsm.start()
            MissionState.reset_fsm_flag = False
            last_voice_step = -1
            last_voice_state = ""
            speak("Mission started. Detecting hand.")

        last_frame_time = time.time()
        frame_counter += 1

        
        if not hasattr(MissionState, '_frame_buffer') or MissionState._frame_buffer.shape != frame.shape:
            MissionState._frame_buffer = np.zeros_like(frame)
        np.copyto(MissionState._frame_buffer, frame)
        MissionState.latest_frame = MissionState._frame_buffer
        MissionState.frame_sequence += 1
        MissionState.is_connected = True

        
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        saturation_ratio = float(np.count_nonzero(v_channel > GLARE_PIXEL_VALUE)) / v_channel.size
        MissionState.glare_saturation = round(saturation_ratio, 3)
        MissionState.is_blinded = saturation_ratio > GLARE_SATURATION_THRESHOLD

        if MissionState.is_blinded:
            
            
            continue

        
        results = yolo_model.track(frame, persist=True, verbose=False, conf=0.75)

        MissionState.yolo_detections = []
        hoi_detections = []
        
        current_step_info = fsm.get_current_step()
        current_expected_prop = current_step_info.object if current_step_info else ""

        
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

        
        skin_cx, skin_cy = detect_skin(frame)
        hand_tracker.update_from_skin(skin_cx, skin_cy)
        
        
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
        if step_age < 0.5 and current_step and current_step.object != "procedure":
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
                    in_view = any(d['class_name'] == current_step.object for d in MissionState.yolo_detections)

        delay = 0.5  

        if in_view:
            fsm._deviation_start = None
            fsm._deviation_obj = None
            if not hasattr(fsm, '_auto_advance_start') or fsm._auto_advance_start is None:
                fsm._auto_advance_start = time.time()
            elif time.time() - fsm._auto_advance_start >= delay:
                detected_action = current_step.action
                detected_obj = current_step.object
                action_conf = 1.0
        else:
            fsm._auto_advance_start = None
            
            
            if current_step.object != "procedure":
                
                allowed_objects = set()
                for i in range(0, fsm.state.current_step_index + 1):
                    allowed_objects.add(fsm.steps[i].object)
                    
                all_detectors = {
                    "hole_puncher": detect_punch_hole,
                    "scissors": detect_scissors,
                    "red_box": detect_red_box,
                    "yellow_box": detect_yellow_box,
                    "open_red_box": detect_open_red_box,
                    "open_yellow_box": detect_open_yellow_box
                }
                    
                out_of_seq_obj_detected = None
                for obj_name, detect_func in all_detectors.items():
                    if obj_name not in allowed_objects:
                        if detect_func(frame):
                            out_of_seq_obj_detected = obj_name
                            break
                                
                if out_of_seq_obj_detected:
                    if getattr(fsm, '_deviation_obj', None) != out_of_seq_obj_detected:
                        fsm._deviation_start = time.time()
                        fsm._deviation_obj = out_of_seq_obj_detected
                    elif time.time() - fsm._deviation_start >= 1.5:  
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
                        
        
        if MissionState.demo_started:
            fsm.process_observation(detected_action, detected_obj, action_conf)
            fsm.save_state_to_disk() 
        
        
        MissionState.fsm_current_state = fsm.state.status
        MissionState.fsm_previous_state = fsm.state.current_step_id or "IDLE"
        MissionState.fsm_current_step = fsm.state.current_step_index
        MissionState.fsm_total_steps = len(fsm.steps)
        MissionState.fsm_deviation_flag = (fsm.state.status == "DEVIATION")
        MissionState.fsm_deviation_details = fsm.state.deviation_details
        MissionState.fsm_debounce_count = fsm._debounce_counter
        MissionState.fsm_expected_action = current_step.action if current_step else ""
        MissionState.fsm_expected_object = current_step.object if current_step else ""

        
        STEP_NAMES = ['Hand detected', 'Red box detected', 'Open red box', 'Punch hole detected', 'Yellow box detected', 'Open yellow box', 'Scissors detected']
        cur_step = MissionState.fsm_current_step
        cur_state = MissionState.fsm_current_state
        
        
        state_changed = (cur_state != last_voice_state) or (cur_step != last_voice_step)
        
        if state_changed:
            
            if cur_state == "IN_PROGRESS" and cur_step > last_voice_step and cur_step > 0:
                if cur_step <= len(STEP_NAMES):
                    msg = f"{STEP_NAMES[cur_step - 1]} complete. Proceeding to next step."
                    speak(msg)
            
            
            if cur_state == "COMPLETED" and last_voice_state != "COMPLETED":
                speak("All steps verified. Experiment procedure complete.")
            
            
            if cur_state == "DEVIATION" and last_voice_state != "DEVIATION":
                detail = MissionState.fsm_deviation_details or "Out of sequence step detected"
                speak(detail)
        
        last_voice_step = cur_step
        last_voice_state = cur_state
        
        
        if MissionState.demo_started and cur_state == "IN_PROGRESS" and current_step and current_step.object != "procedure":
            if step_age >= 8.0 and not getattr(fsm, '_step_reminder_given', False):
                obj_name = current_step.object.replace('_', ' ')
                speak(f"Please show {obj_name}. step need to perform.")
                fsm._step_reminder_given = True

        
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
