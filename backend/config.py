from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./nautica.db"
    S3_UPLOAD_BUCKET: str = "nautica-uploads"
    S3_RESULTS_BUCKET: str = "nautica-results"
    AWS_REGION: str = "us-east-1"
    FRAME_STRIDE: int = 10
    MAX_FRAMES: int = 300
    YOLO_MODEL: str = "yolov8m.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.20
    YOLO_MAX_DETECTIONS: int = 50
    IOU_THRESHOLD: float = 0.2
    MAX_FRAMES_LOST: int = 5
    TRACKING_MIN_CONFIDENCE: float = 0.3
    PLAYBACK_TARGET_FPS: int = 10

    # Anomaly detection
    LOITERING_MIN_FRAMES: int = 15
    LOITERING_MAX_DISPLACEMENT_PX: float = 50.0
    LOITERING_CRITICAL_FRAMES: int = 30
    CONVERGENCE_DISTANCE_PX: float = 150.0
    CONVERGENCE_MIN_VESSELS: int = 2
    CONVERGENCE_MIN_FRAMES: int = 3
    RESTRICTED_ZONES: list = [
        {"name": "Harbor Restricted", "x": 0, "y": 0, "width": 400, "height": 300}
    ]
    ABRUPT_MOTION_PX_PER_FRAME: float = 200.0

    class Config:
        env_file = ".env"


settings = Settings()
