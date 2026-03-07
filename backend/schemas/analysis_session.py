from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SessionCreate(BaseModel):
    name: str
    file_type: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    name: str
    status: str
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    source_filename: Optional[str] = None
    frame_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionList(BaseModel):
    sessions: List[SessionResponse]
