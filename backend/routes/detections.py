from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from schemas.detection import DetectionResponse, DetectionList
from utils.mock_loader import load_mock

router = APIRouter()


@router.get("/sessions/{session_id}/detections", response_model=DetectionList)
def get_detections(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    mock_data = load_mock("detections.json")
    detections = [
        DetectionResponse(
            id=d["id"],
            track_id=d.get("track_id"),
            object_type=d.get("object_type"),
            confidence=d.get("confidence"),
            position=d.get("position"),
            status=d.get("status"),
            frame_number=d.get("frame_number"),
        )
        for d in mock_data
        if d.get("session_id") == session_id
    ]

    return DetectionList(detections=detections)
