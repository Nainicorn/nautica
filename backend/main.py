from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base, SessionLocal
from utils.mock_loader import load_mock


import models.analysis_session  # noqa: F401
import models.detection  # noqa: F401
import models.anomaly  # noqa: F401
import models.report  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    _seed_sessions()
    _ensure_uploads_dir()
    yield


def _migrate_columns():
    """Add missing columns to existing tables (dev-only migration)."""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("analysis_sessions")}
    with engine.connect() as conn:
        if "frame_count" not in columns:
            conn.execute(text("ALTER TABLE analysis_sessions ADD COLUMN frame_count INTEGER"))
            conn.commit()


def _ensure_uploads_dir():
    from pathlib import Path
    uploads = Path(__file__).resolve().parent / "uploads"
    uploads.mkdir(exist_ok=True)


def _seed_sessions():
    from models.analysis_session import AnalysisSession
    db = SessionLocal()
    try:
        count = db.query(AnalysisSession).count()
        if count == 0:
            sessions_data = load_mock("sessions.json")
            for s in sessions_data:
                session = AnalysisSession(
                    id=s["id"],
                    name=s["name"],
                    status=s["status"],
                    file_path=s.get("file_path"),
                    file_type=s.get("file_type"),
                    source_filename=s.get("source_filename"),
                )
                db.add(session)
            db.commit()
    finally:
        db.close()


app = FastAPI(
    title="Nautica AI",
    description="Maritime Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.health import router as health_router
from routes.sessions import router as sessions_router
from routes.upload import router as upload_router
from routes.detections import router as detections_router
from routes.anomalies import router as anomalies_router
from routes.reports import router as reports_router
from routes.playback import router as playback_router

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(detections_router, prefix="/api", tags=["detections"])
app.include_router(anomalies_router, prefix="/api", tags=["anomalies"])
app.include_router(reports_router, prefix="/api", tags=["reports"])
app.include_router(playback_router, prefix="/api", tags=["playback"])

app.mount(
    "/api/uploads",
    StaticFiles(directory=Path(__file__).resolve().parent / "uploads"),
    name="uploads",
)
