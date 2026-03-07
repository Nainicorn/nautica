from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from models.detection import Detection as DetectionModel
from schemas.detection import DetectionResponse, DetectionList
from utils.mock_loader import load_mock

router = APIRouter()


@router.get("/sessions/{session_id}/detections", response_model=DetectionList)
def get_detections(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Query real detections from database first
    db_detections = (
        db.query(DetectionModel)
        .filter(DetectionModel.session_id == session_id)
        .order_by(DetectionModel.frame_number)
        .all()
    )

    if db_detections:
        detections = [
            DetectionResponse(
                id=d.id,
                track_id=d.track_id,
                object_type=d.object_type,
                confidence=d.confidence,
                position=f"({d.x:.0f}, {d.y:.0f})" if d.x is not None else None,
                status="UNTRACKED" if not d.track_id else "TRACKED",
                frame_number=d.frame_number,
                vessel_size=d.vessel_size,
            )
            for d in db_detections
        ]
        return DetectionList(detections=detections)

    # Fallback to mock data for demo sessions
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
