from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReportResponse(BaseModel):
    session_id: Optional[str] = None
    summary: Optional[str] = None
    anomalies_text: Optional[str] = None
    recommendation: Optional[str] = None
    generated_at: Optional[datetime] = None
