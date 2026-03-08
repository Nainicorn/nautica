from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from config import settings


import models.analysis_session  # noqa: F401
import models.detection  # noqa: F401
import models.anomaly  # noqa: F401
import models.report  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    _ensure_uploads_dir()
    yield


def _migrate_columns():
    """Add missing columns to existing tables (dev-only migration)."""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    session_cols = {col["name"] for col in inspector.get_columns("analysis_sessions")}
    detection_cols = {col["name"] for col in inspector.get_columns("detections")}
    anomaly_cols = {col["name"] for col in inspector.get_columns("anomalies")}
    with engine.connect() as conn:
        if "frame_count" not in session_cols:
            conn.execute(text("ALTER TABLE analysis_sessions ADD COLUMN frame_count INTEGER"))
        if "vessel_size" not in detection_cols:
            conn.execute(text("ALTER TABLE detections ADD COLUMN vessel_size TEXT"))
        if "frame_number" not in anomaly_cols:
            conn.execute(text("ALTER TABLE anomalies ADD COLUMN frame_number INTEGER DEFAULT 0"))
        if "meta" not in anomaly_cols:
            conn.execute(text("ALTER TABLE anomalies ADD COLUMN meta TEXT"))
        conn.commit()


def _ensure_uploads_dir():
    settings.uploads_path.mkdir(parents=True, exist_ok=True)



app = FastAPI(
    title="Nautica AI",
    description="Maritime Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
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
    StaticFiles(directory=settings.uploads_path),
    name="uploads",
)
