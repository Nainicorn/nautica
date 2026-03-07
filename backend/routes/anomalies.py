from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from schemas.anomaly import AnomalyResponse, AnomalyList
from utils.mock_loader import load_mock

router = APIRouter()


@router.get("/sessions/{session_id}/anomalies", response_model=AnomalyList)
def get_anomalies(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    mock_data = load_mock("anomalies.json")
    anomalies = [AnomalyResponse(**a) for a in mock_data if a.get("session_id") == session_id]

    return AnomalyList(anomalies=anomalies)
