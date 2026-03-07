from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    file_size: int
    status: str = "uploaded"
