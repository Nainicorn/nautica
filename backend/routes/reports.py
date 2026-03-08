import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models.analysis_session import AnalysisSession
from models.detection import Detection
from models.anomaly import Anomaly
from models.report import Report
from schemas.report import ReportResponse
from utils.mock_loader import load_mock
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions/{session_id}/report", response_model=ReportResponse)
def get_report(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Try real DB record first
    report = db.query(Report).filter(Report.session_id == session_id).first()
    if report:
        return ReportResponse(
            session_id=report.session_id,
            summary=report.summary,
            anomalies_text=report.anomalies_text,
            recommendation=report.recommendation,
            generated_at=report.generated_at,
        )

    # Fall back to mock data
    mock_data = load_mock("reports.json")

    if isinstance(mock_data, dict) and mock_data.get("session_id") == session_id:
        return ReportResponse(**mock_data)

    if isinstance(mock_data, list):
        for r in mock_data:
            if r.get("session_id") == session_id:
                return ReportResponse(**r)

    return ReportResponse(session_id=session_id)


@router.get("/sessions/{session_id}/report/stream")
def stream_report(session_id: str):
    """SSE endpoint that streams the AI report word-by-word from Gemini."""
    db = SessionLocal()

    try:
        session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not session:
            db.close()
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        if not settings.GEMINI_API_KEY:
            db.close()
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        # Load tracking artifact
        uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
        tracks_path = uploads_dir / session_id / "tracking" / "tracks.json"
        tracks_data = None
        if tracks_path.exists():
            with open(tracks_path) as f:
                tracks_data = json.load(f)

        detections = (
            db.query(Detection)
            .filter(Detection.session_id == session_id)
            .order_by(Detection.frame_number)
            .all()
        )
        anomalies = (
            db.query(Anomaly)
            .filter(Anomaly.session_id == session_id)
            .all()
        )
    except HTTPException:
        raise
    except Exception:
        db.close()
        raise

    from services.report_service import report_service

    def event_generator():
        full_text = ""
        try:
            session.status = "generating_report"
            db.commit()

            for chunk in report_service.generate_stream(
                session_id, detections, anomalies, tracks_data
            ):
                full_text += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Save report to DB
            db.query(Report).filter(Report.session_id == session_id).delete()
            db.commit()

            generated_at = datetime.now(timezone.utc)
            report = Report(
                id=f"rpt_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                summary=full_text.strip(),
                anomalies_text=None,
                recommendation=None,
                generated_at=generated_at,
            )
            db.add(report)
            db.commit()

            # Save artifact
            reports_dir = uploads_dir / session_id / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            artifact = {
                "session_id": session_id,
                "generated_at": generated_at.isoformat(),
                "model": settings.LLM_MODEL,
                "summary": full_text.strip(),
            }
            with open(reports_dir / "report.json", "w") as f:
                json.dump(artifact, f, indent=2)

            session.status = "report_complete"
            db.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

            logger.info(f"Session {session_id}: streamed report complete")

        except Exception as e:
            session.status = "failed"
            db.commit()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
