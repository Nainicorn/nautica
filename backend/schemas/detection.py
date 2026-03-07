from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel


class DetectionResponse(BaseModel):
    id: str
    track_id: Optional[str] = None
    object_type: Optional[str] = None
    confidence: Optional[float] = None
    position: Optional[str] = None
    status: Optional[str] = None
    frame_number: Optional[int] = None


class DetectionList(BaseModel):
    detections: List[DetectionResponse]
