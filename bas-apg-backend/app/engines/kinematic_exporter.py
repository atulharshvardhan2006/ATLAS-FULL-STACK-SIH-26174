"""
BAS-APG — Kinematic Exporter

Converts OpenCV solvePnP rotation/translation vectors into
clean Pitch, Yaw, Roll (Euler Angles) for the Digital Twin.
"""

import cv2
import numpy as np

def extract_kinematics(rvec, tvec):
    """
    Converts rvec and tvec from solvePnP to Euler angles and translation.
    Returns:
        dict: {"x": float, "y": float, "z": float, "pitch": float, "yaw": float, "roll": float}
    """
    if rvec is None or tvec is None:
        return {"x": 0.0, "y": 0.0, "z": 0.0, "pitch": 0.0, "yaw": 0.0, "roll": 0.0}

    
    rotation_matrix, _ = cv2.Rodrigues(rvec)

    
    sy = np.sqrt(
        rotation_matrix[0, 0] * rotation_matrix[0, 0]
        + rotation_matrix[1, 0] * rotation_matrix[1, 0]
    )
    singular = sy < 1e-6

    if not singular:
        x = np.math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])  
        y = np.math.atan2(-rotation_matrix[2, 0], sy)  
        z = np.math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])  
    else:
        x = np.math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        y = np.math.atan2(-rotation_matrix[2, 0], sy)
        z = 0

    return {
        "x": float(tvec[0][0]),
        "y": float(tvec[1][0]),
        "z": float(tvec[2][0]),
        "pitch": float(np.degrees(y)),
        "yaw": float(np.degrees(z)),
        "roll": float(np.degrees(x)),
    }
