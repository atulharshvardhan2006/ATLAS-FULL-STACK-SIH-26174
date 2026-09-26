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

    # Crew Safety & Proximity Tracking
    crew_safety_active: bool = True
    crew_telemetry: list = []           # [{crew_id, status, centroid, bbox, velocity_px, ...}]
    crew_hazard_objects: list = ["red_box", "yellow_box", "scissors", "hole_puncher"]

    # ─── FEATURE 1: KINETIC JERK & SLOSH GUARD ───────────────────────────────
    jerk_magnitude: float = 0.0          # Current jerk (derivative of acceleration) in px/s³
    slosh_alert: bool = False            # True when jerk exceeds threshold
    slosh_alert_text: str = ""           # Alert message for HUD display
    
    # ─── FEATURE 2: SWaP-C ECO-GOVERNOR ──────────────────────────────────────
    eco_governor_mode: str = "ACTIVE"    # ACTIVE (30 FPS) or STANDBY (5 FPS)
    eco_governor_fps: float = 30.0       # Current governed FPS target
    eco_frames_skipped: int = 0          # Total frames skipped in standby
    
    # ─── FEATURE 3: MERKLE CRYPTOGRAPHIC FLIGHT RECORDER ─────────────────────
    merkle_chain_hash: str = ""          # Current head of the SHA-256 hash chain
    merkle_chain_length: int = 0         # Total entries in the hash chain
    
    # ─── FEATURE 4: HESITATION & COGNITIVE STALL DETECTOR ────────────────────
    hesitation_count: int = 0            # Number of hesitation events this session
    hesitation_active: bool = False      # True when operator is currently stalling
    hesitation_dwell_ms: float = 0.0     # How long the hand has been hovering
    
    # ─── FEATURE 5: FOD VECTOR PROJECTION ────────────────────────────────────
    fod_projection_active: bool = False  # True when a drift trajectory is being drawn
    fod_projected_object: str = ""       # Name of the drifting object
    fod_impact_eta_s: float = 0.0        # Estimated seconds to predicted impact
    
    # ─── CCSDS SPACE PACKET PROTOCOL ─────────────────────────────────────────
    ccsds_last_hex: str = ""             # Last CCSDS packet hex dump (truncated)
    ccsds_total_packets: int = 0         # Total packets formatted this session
    ccsds_total_bytes: int = 0           # Total bytes packed
    ccsds_last_apid: str = ""            # Last APID (hex string)
    ccsds_last_apid_name: str = ""       # Human-readable APID name
    ccsds_active_apids: int = 0          # Number of active subsystem streams
