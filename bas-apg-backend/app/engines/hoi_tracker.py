"""
BAS-APG — Hand-Object Interaction (HOI) Tracker

Determines hand-object interactions using Velocity Correlation (Pearson's r)
and Real-World Metric Space distances.

State machine per (hand, object) pair:
    FAR ──(distance < threshold)──→ NEAR ──(high velocity correlation)──→ HELD
     ↑                                ↓
     └──────(distance > threshold)────┘
"""

import json
import math
import os  
from collections import defaultdict

import numpy as np
from scipy.stats import pearsonr

from app.core.config import get_settings

class HOITracker:
    """Tracks hand-object interactions across frames using Velocity Correlation.

    Args:
        contact_threshold_mm: Distance in millimeters below which hand is "NEAR".
        velocity_correlation_threshold: Pearson's r threshold (e.g., 0.7) for HELD.
        history_size: Number of frames to track for velocity calculation (default 15).
        calibration_path: Path to camera intrinsic calibration JSON.
    """

    def __init__(
        self,
        contact_threshold_mm: int = 100,
        velocity_correlation_threshold: float = 0.7,
        history_size: int = 15,
        calibration_path: str = "data/camera_calibration.json",
    ):
        self.contact_threshold = contact_threshold_mm
        self.corr_threshold = velocity_correlation_threshold
        self.history_size = history_size

        
        self.tau_upper = 0.75
        self.tau_lower = 0.50

        
        self.camera_matrix = None
        self.nominal_depth_mm = 500.0  
        if os.path.exists(calibration_path):
            try:
                with open(calibration_path, "r") as f:
                    calib = json.load(f)
                    self.camera_matrix = np.array(calib["camera_matrix"])
                    print(
                        f"[HOI] Loaded camera calibration: fx={self.camera_matrix[0,0]:.1f}, fy={self.camera_matrix[1,1]:.1f}"
                    )
            except Exception as e:
                print(f"[HOI] WARNING: Failed to load calibration: {e}")

        
        self.hand_history = []
        
        self.obj_history: dict[int, list[tuple[float, float]]] = defaultdict(list)

        
        self.interaction_states: dict[int, str] = defaultdict(lambda: "FAR")

        self.settings = get_settings()
        self.hand_velocity_history = []

        
        self._class_map: dict[int, str] = {}

    def _pixel_to_metric(
        self, px: float, py: float, depth_mm: float
    ) -> tuple[float, float]:
        """Convert 2D pixel coordinate to 3D metric coordinate (X, Y) given Z depth."""
        if self.camera_matrix is not None:
            fx = self.camera_matrix[0, 0]
            fy = self.camera_matrix[1, 1]
            cx = self.camera_matrix[0, 2]
            cy = self.camera_matrix[1, 2]
            x_mm = (px - cx) * depth_mm / fx
            y_mm = (py - cy) * depth_mm / fy
            return (x_mm, y_mm)
        else:
            
            return (float(px), float(py))

    def _calculate_velocity(
        self, history: list[tuple[float, float, float]]
    ) -> list[float]:
        """Calculate velocity magnitudes from position history in 3D."""
        if len(history) < 2:
            return []
        velocities = []
        for i in range(1, len(history)):
            dx = history[i][0] - history[i - 1][0]
            dy = history[i][1] - history[i - 1][1]
            dz = history[i][2] - history[i - 1][2]
            velocities.append(math.sqrt(dx**2 + dy**2 + dz**2))
        return velocities

    def compute_interactions(
        self, palm_center: tuple[int, int] | None, detections: list[dict]
    ) -> list[dict]:
        """Compute interaction state for each detected object using Velocity Correlation.

        Args:
            palm_center: (x, y) pixel coordinates of the palm.
            detections: list of dicts with keys: class, track_id, bbox, confidence.

        Returns:
            list of dicts with keys: class, track_id, state (FAR/NEAR/HELD), distance.
        """
        results = []
        current_track_ids = set()

        
        palm_z = self.nominal_depth_mm
        if palm_center:
            palm_metric = self._pixel_to_metric(palm_center[0], palm_center[1], palm_z)
            self.hand_history.append((palm_metric[0], palm_metric[1], palm_z))
            if len(self.hand_history) > self.history_size:
                self.hand_history.pop(0)
        else:
            self.hand_history.clear()

        hand_velocities = self._calculate_velocity(self.hand_history)

        for det in detections:
            track_id = det.get("track_id", -1)
            if track_id == -1:
                continue

            current_track_ids.add(track_id)
            bbox = det["bbox"]  
            class_name = det["class"]

            self._class_map[track_id] = class_name

            
            obj_cx = int((bbox[0] + bbox[2]) / 2)
            obj_cy = int((bbox[1] + bbox[3]) / 2)

            obj_z = self.nominal_depth_mm
            obj_metric = self._pixel_to_metric(obj_cx, obj_cy, obj_z)

            self.obj_history[track_id].append((obj_metric[0], obj_metric[1], obj_z))
            if len(self.obj_history[track_id]) > self.history_size:
                self.obj_history[track_id].pop(0)

            if not palm_center or len(self.hand_history) < 5:
                
                self.interaction_states[track_id] = "FAR"
                results.append(
                    {
                        "class": class_name,
                        "track_id": track_id,
                        "state": "FAR",
                        "distance": float("inf"),
                    }
                )
                continue

            
            distance_mm = math.sqrt(
                (palm_metric[0] - obj_metric[0]) ** 2
                + (palm_metric[1] - obj_metric[1]) ** 2
                + (palm_z - obj_z) ** 2
            )

            if distance_mm < self.contact_threshold:
                
                obj_velocities = self._calculate_velocity(self.obj_history[track_id])

                
                min_len = min(len(hand_velocities), len(obj_velocities))
                if min_len >= 5:
                    h_vel = hand_velocities[-min_len:]
                    o_vel = obj_velocities[-min_len:]

                    
                    if np.std(h_vel) > 1e-5 and np.std(o_vel) > 1e-5:
                        r, _ = pearsonr(h_vel, o_vel)
                    else:
                        
                        r = (
                            1.0
                            if np.mean(h_vel) < 5.0 and np.mean(o_vel) < 5.0
                            else 0.0
                        )

                    
                    current_state = self.interaction_states.get(track_id, "NEAR")
                    if r >= self.tau_upper:
                        self.interaction_states[track_id] = "HELD"
                    elif r <= self.tau_lower:
                        self.interaction_states[track_id] = "NEAR"
                    else:
                        
                        self.interaction_states[track_id] = current_state
                else:
                    self.interaction_states[track_id] = "NEAR"
            else:
                self.interaction_states[track_id] = "FAR"

            results.append(
                {
                    "class": class_name,
                    "track_id": track_id,
                    "state": self.interaction_states[track_id],
                    "distance": round(distance_mm, 1),
                }
            )

        
        for tid in list(self.obj_history.keys()):
            if tid not in current_track_ids:
                del self.obj_history[tid]
                if tid in self.interaction_states:
                    del self.interaction_states[tid]

        return results

    def get_held_objects(self) -> list[str]:
        """Return class names of all currently HELD objects."""
        return [
            self._class_map.get(tid, "unknown")
            for tid, state in self.interaction_states.items()
            if state == "HELD"
        ]

    def update_immobility_status(self, current_velocity_magnitude: float) -> str:
        """
        Immobility Guardian: Checks if hand variance drops below threshold for 30s.
        """
        import numpy as np

        self.hand_velocity_history.append(current_velocity_magnitude)

        
        if len(self.hand_velocity_history) > self.settings.immobility_frames:
            self.hand_velocity_history.pop(0)

            
            velocity_variance = np.var(self.hand_velocity_history)

            if velocity_variance < self.settings.immobility_variance_threshold:
                return "CREW_EMERGENCY_IMMOBILITY"
        return "NOMINAL"

    def reset(self):
        """Reset all tracking state."""
        self.hand_history.clear()
        self.obj_history.clear()
        self.interaction_states.clear()
        self._class_map.clear()
