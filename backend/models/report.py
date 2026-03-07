from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("analysis_sessions.id"), nullable=False)
    summary = Column(Text, nullable=True)
    anomalies_text = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now())
