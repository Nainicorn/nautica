from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel


class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class FrameDetection(BaseModel):
    track_id: Optional[str] = None
    object_type: Optional[str] = None
    confidence: Optional[float] = None
    bbox: BBox


class FrameOverlay(BaseModel):
    frame_number: int
    detections: List[FrameDetection]


class OverlayResponse(BaseModel):
    session_id: str
    frame_count: int
    playback_target_fps: int
    frames: List[FrameOverlay]
