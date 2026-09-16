"""
BAS-APG — Application Configuration

Loads settings from environment variables and .env file.
All thresholds and paths are configurable without code changes.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    app_name: str = "BAS AI Procedure Guardian"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, alias="APG_DEBUG")

    host: str = Field(default="0.0.0.0", alias="APG_HOST")
    port: int = Field(default=8000, alias="APG_PORT")

    camera_index: int = Field(default=0, alias="APG_CAMERA_INDEX")
    camera_width: int = Field(default=640, alias="APG_CAMERA_WIDTH")
    camera_height: int = Field(default=480, alias="APG_CAMERA_HEIGHT")
    camera_fps: int = Field(default=30, alias="APG_CAMERA_FPS")

    
    yolo_model_path: str = Field(default="data/models/best.pt", alias="APG_YOLO_MODEL")
    use_onnx: bool = Field(default=False, alias="APG_USE_ONNX")
    yolo_model_path_onnx: str = Field(
        default="data/models/best.onnx", alias="APG_YOLO_MODEL_ONNX"
    )
    yolo_confidence: float = Field(default=0.25, alias="APG_YOLO_CONF")
    use_mps: bool = Field(default=False, alias="APG_USE_MPS")  

    
    hand_detection_confidence: float = Field(default=0.7, alias="APG_HAND_DET_CONF")
    hand_tracking_confidence: float = Field(default=0.5, alias="APG_HAND_TRACK_CONF")
    max_hands: int = Field(default=2, alias="APG_MAX_HANDS")

  
    contact_threshold_px: int = Field(
        default=120, alias="APG_CONTACT_THRESHOLD"
    )  
    contact_threshold_mm: int = Field(
        default=100, alias="APG_CONTACT_THRESHOLD_MM"
    )  
    held_frame_count: int = Field(
        default=5, alias="APG_HELD_FRAMES"
    )  
    velocity_correlation_threshold: float = Field(
        default=0.72, alias="APG_VELOCITY_CORRELATION_THRESHOLD"
    )  

    
    debounce_frames: int = Field(
        default=15, alias="APG_DEBOUNCE_FRAMES"
    )  
    procedure_path: str = Field(
        default="data/procedures/red_yellow_box_experiment.json",
        alias="APG_PROCEDURE_PATH",
    )

    
    latency_profiling: bool = Field(default=True, alias="APG_LATENCY_PROFILING")
    camera_calibration_path: str = Field(
        default="data/camera_calibration.json", alias="APG_CAMERA_CALIBRATION"
    )

    
    immobility_frames: int = Field(default=900, alias="APG_IMMOBILITY_FRAMES")
    immobility_variance_threshold: float = Field(
        default=0.5, alias="APG_IMMOBILITY_VARIANCE_THRESHOLD"
    )
    rack_boundary_z_max: float = Field(default=500.0, alias="APG_RACK_BOUNDARY_Z_MAX")

    
    db_path: str = Field(default="data/evidence_logs/bas_apg.db", alias="APG_DB_PATH")

    
    tts_rate: int = Field(default=160, alias="APG_TTS_RATE")  
    tts_enabled: bool = Field(default=True, alias="APG_TTS_ENABLED")

    
    jpeg_quality: int = Field(default=80, alias="APG_JPEG_QUALITY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
