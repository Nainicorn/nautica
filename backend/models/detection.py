from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("analysis_sessions.id"), nullable=False)
    track_id = Column(String, nullable=True)
    object_type = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    frame_number = Column(Integer, nullable=True)
    vessel_size = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
