import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.analysis_session import AnalysisSession
from models.detection import Detection
from schemas.analysis_session import SessionCreate, SessionResponse, SessionList
from services.video_service import video_service

router = APIRouter()


@router.get("/sessions", response_model=SessionList)
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).all()
    return SessionList(sessions=[SessionResponse.model_validate(s) for s in sessions])


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return SessionResponse.model_validate(session)


@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    session = AnalysisSession(
        id=f"session_{uuid.uuid4().hex[:12]}",
        name=data.name,
        status="pending",
        file_type=data.file_type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"


@router.post("/sessions/{session_id}/process", response_model=SessionResponse)
def process_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if session.status != "uploaded":
        raise HTTPException(
            status_code=409,
            detail=f"Session status is '{session.status}', expected 'uploaded'",
        )

    session.status = "processing"
    db.commit()

    try:
        source_path = UPLOADS_DIR.parent / session.file_path
        frames_dir = UPLOADS_DIR / session_id / "frames"

        result = video_service.extract_frames(str(source_path), str(frames_dir))

        session.status = "extracted"
        session.frame_count = result["frame_count"]
        db.commit()
        db.refresh(session)

    except Exception as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(e)}")

    return SessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=200)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    db.query(Detection).filter(Detection.session_id == session_id).delete()

    db.delete(session)
    db.commit()

    session_dir = UPLOADS_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)

    return {"detail": f"Session '{session_id}' deleted"}


@router.post("/sessions/{session_id}/detect", response_model=SessionResponse)
def detect_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if session.status != "extracted":
        raise HTTPException(
            status_code=409,
            detail=f"Session status is '{session.status}', expected 'extracted'",
        )

    try:
        from services.detection_service import run_detection_pipeline

        result = run_detection_pipeline(session_id, db)
        db.refresh(session)

    except Exception as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

    response = SessionResponse.model_validate(session)
    return {
        **response.model_dump(),
        "detection_count": result["detection_count"],
        "frames_processed": result["frames_processed"],
    }
