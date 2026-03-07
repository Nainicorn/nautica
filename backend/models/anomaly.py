from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("analysis_sessions.id"), nullable=False)
    anomaly_type = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    track_ids = Column(Text, nullable=True)  # JSON string, parsed in schema layer
    meta = Column(Text, nullable=True)
    frame_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
