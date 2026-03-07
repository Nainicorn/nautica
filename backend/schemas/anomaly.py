from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AnomalyResponse(BaseModel):
    id: str
    anomaly_type: str
    severity: Optional[str] = None
    description: Optional[str] = None
    track_ids: Optional[List[str]] = None
    meta: Optional[str] = None
    created_at: Optional[datetime] = None


class AnomalyList(BaseModel):
    anomalies: List[AnomalyResponse]
