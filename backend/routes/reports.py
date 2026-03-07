from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from schemas.report import ReportResponse
from utils.mock_loader import load_mock

router = APIRouter()


@router.get("/sessions/{session_id}/report", response_model=ReportResponse)
def get_report(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    mock_data = load_mock("reports.json")

    if isinstance(mock_data, dict) and mock_data.get("session_id") == session_id:
        return ReportResponse(**mock_data)

    if isinstance(mock_data, list):
        for r in mock_data:
            if r.get("session_id") == session_id:
                return ReportResponse(**r)

    return ReportResponse(session_id=session_id)
