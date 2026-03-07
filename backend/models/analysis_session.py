from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from database import Base


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, default="pending")
    file_path = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    source_filename = Column(String, nullable=True)
    frame_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
