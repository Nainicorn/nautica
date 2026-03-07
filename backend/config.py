from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str = "sqlite:///./nautica.db"
    S3_UPLOAD_BUCKET: str = "nautica-uploads"
    S3_RESULTS_BUCKET: str = "nautica-results"
    AWS_REGION: str = "us-east-1"
    FRAME_STRIDE: int = 10
    MAX_FRAMES: int = 300
    YOLO_MODEL: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25
    YOLO_MAX_DETECTIONS: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
