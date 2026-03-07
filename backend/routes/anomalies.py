import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from models.anomaly import Anomaly as AnomalyModel
from schemas.anomaly import AnomalyResponse, AnomalyList
from utils.mock_loader import load_mock

router = APIRouter()


@router.get("/sessions/{session_id}/anomalies", response_model=AnomalyList)
def get_anomalies(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Query real anomalies from database first
    db_anomalies = (
        db.query(AnomalyModel)
        .filter(AnomalyModel.session_id == session_id)
        .order_by(AnomalyModel.created_at.desc())
        .all()
    )

    if db_anomalies:
        anomalies = []
        for a in db_anomalies:
            track_ids = None
            if a.track_ids:
                try:
                    track_ids = json.loads(a.track_ids)
                except (json.JSONDecodeError, TypeError):
                    track_ids = [a.track_ids]

            anomalies.append(AnomalyResponse(
                id=a.id,
                anomaly_type=a.anomaly_type,
                severity=a.severity,
                description=a.description,
                track_ids=track_ids,
                meta=a.meta,
                frame_number=a.frame_number,
                created_at=a.created_at,
            ))
        return AnomalyList(anomalies=anomalies)

    # Fallback to mock data for demo sessions
    mock_data = load_mock("anomalies.json")
    anomalies = [
        AnomalyResponse(**a)
        for a in mock_data
        if a.get("session_id") == session_id
    ]

    return AnomalyList(anomalies=anomalies)
