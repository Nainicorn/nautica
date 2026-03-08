from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from config import settings
from models.analysis_session import AnalysisSession
from schemas.upload import UploadResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Set status to uploading
    session.status = "uploading"
    db.commit()

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=413, detail="File exceeds 200MB limit")

    # Save file
    dest_dir = settings.uploads_path / session_id / "source"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename

    with open(dest_path, "wb") as f:
        f.write(content)

    # Determine file type category
    file_type = "image" if ext in {".jpg", ".jpeg", ".png"} else "video"

    # Update session
    session.status = "uploaded"
    session.file_path = str(dest_path.relative_to(settings.uploads_path.parent))
    session.source_filename = file.filename
    session.file_type = file_type
    db.commit()
    db.refresh(session)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        file_size=len(content),
        status="uploaded",
    )
