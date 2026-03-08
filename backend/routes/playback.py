import re
from pathlib import Path
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from config import settings
from models.analysis_session import AnalysisSession
from models.detection import Detection as DetectionModel
from schemas.playback import BBox, FrameDetection, FrameOverlay, OverlayResponse

router = APIRouter()



@router.get("/sessions/{session_id}/overlay", response_model=OverlayResponse)
def get_overlay(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    frames_dir = settings.uploads_path / session_id / "frames"
    frame_numbers = _list_frame_numbers(frames_dir)
    frame_count = len(frame_numbers)

    if frame_count == 0:
        raise HTTPException(status_code=404, detail="No frames found for this session")

    detections = (
        db.query(DetectionModel)
        .filter(DetectionModel.session_id == session_id)
        .order_by(DetectionModel.frame_number, DetectionModel.track_id)
        .all()
    )

    grouped = defaultdict(list)
    for d in detections:
        if d.frame_number is not None and d.x is not None:
            grouped[d.frame_number].append(
                FrameDetection(
                    track_id=d.track_id,
                    object_type=d.object_type,
                    confidence=d.confidence,
                    vessel_size=d.vessel_size,
                    bbox=BBox(x=d.x, y=d.y, width=d.width, height=d.height),
                )
            )

    frames = [
        FrameOverlay(
            frame_number=fn,
            detections=grouped.get(fn, []),
        )
        for fn in frame_numbers
    ]

    return OverlayResponse(
        session_id=session_id,
        frame_count=frame_count,
        playback_target_fps=settings.PLAYBACK_TARGET_FPS,
        frames=frames,
    )


def _list_frame_numbers(frames_dir: Path) -> list[int]:
    if not frames_dir.is_dir():
        return []
    pattern = re.compile(r"^frame_(\d+)\.jpg$")
    numbers = []
    for f in frames_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            numbers.append(int(m.group(1)))
    numbers.sort()
    return numbers
