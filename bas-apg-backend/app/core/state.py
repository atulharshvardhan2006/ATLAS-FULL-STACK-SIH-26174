from typing import Optional
import numpy as np

class MissionState:
    """Thread-safe shared state between FastAPI routes and the AI engine.
    
    The AI engine thread WRITES to these fields.
    The FastAPI WebSocket/MJPEG threads READ from them.
    Python's GIL guarantees atomic reference assignment for simple types.
    """
    
    
    active_session_id: Optional[str] = None
    demo_started: bool = False
    reset_fsm_flag: bool = False
    auth_status: str = "LOCKED"  # LOCKED, SCANNING, GRANTED, DENIED, SAFETY_HAND, SAFETY_GLOVES, SAFETY_GLASSES
    
    
    latest_frame: Optional[np.ndarray] = None
    frame_sequence: int = 0
    frame_width: int = 1920
    frame_height: int = 1080
    is_connected: bool = False
    aruco_detected: bool = False
    glare_saturation: float = 0.0
    is_blinded: bool = False
    
    
    yolo_detections: list = []        
    inference_ms: float = 0.0
    fps: float = 0.0
    
    
    hand_detected: bool = False
    hand_wrist: Optional[list] = None       
    hand_fingertip: Optional[list] = None   
    hand_velocity: float = 0.0
    hand_is_immobile: bool = True
    
    
    pearson_r: float = 0.0
    is_grasping: bool = False
    grasped_object: Optional[str] = None
    
    
    fsm_current_state: str = "IDLE"
    fsm_previous_state: str = "IDLE"
    fsm_current_step: int = 0
    fsm_total_steps: int = 7
    fsm_deviation_flag: bool = False
    fsm_deviation_details: str = ""
    fsm_debounce_count: int = 0
    fsm_expected_action: str = ""
    fsm_expected_object: str = ""
    fsm_wizard_override: bool = False
    
    # Dynamic experiment selection
    selected_procedure: str = "data/procedures/red_yellow_box_experiment.json"
    frontend_target: Optional[str] = None
    
    
    z_offset_mm: float = 0.0
    z_boundary_mm: float = 500.0
    norm_boundary_y: float = 0.72
    containment_breach: bool = False
    
    
    kalman_coasting: bool = False
    kalman_coast_frames: int = 0
    
    
    standby_mode: bool = False
    isp_settling: bool = True
    isp_remaining_s: float = 10.0
    ram_usage_mb: int = 0
    usb_status: str = "CONNECTED"
    system_status: str = "BOOTING"
    recent_logs: list = []
