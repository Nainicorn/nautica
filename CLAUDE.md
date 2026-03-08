# Nautica AI — Project Context & Architecture

---

## Constraints

- Update `claude.md` every time a major task is COMPLETED or code is edited
- Always critically analyze the plan before acting — suggest improvements when necessary
- Use plan mode every time you plan the next phase or set of tasks
- In plan mode, break each task into sub-tasks and complete them one at a time before moving on
- When a task is done, remove its context from `claude.md` and move it to `COMPLETED.md`
- `claude.md` should only ever contain: project overview, stack, flow, structure, remaining steps, and constraints
- `COMPLETED.md` should be a running log of everything implemented at each stage
- Notify the user before compacting
- When compacting, read the previous chat + `COMPLETED.md` + `claude.md` together to retain full scope
- Notify the user if something requires manual action that you cannot complete

---

## What Is Nautica AI?

Nautica AI is a visual maritime vessel tracking and analysis system. You upload drone footage, aerial video, or images. The system processes them through a computer vision pipeline — detecting vessels, tracking them across frames, and rendering annotated visual results. Anomaly alerts and intelligence reports are secondary layers built on top of tracked detection data.

**Core product output:** Annotated video playback with tracked vessel IDs and detection overlays.

---

## How It Works

1. Upload footage (video or image)
2. Extract frames (OpenCV, stride-based)
3. Run YOLOv8 detection on each frame
4. Track objects across frames (IoU + Hungarian assignment, persistent VES-XXX IDs)
5. Render annotated visual playback (canvas overlays)
6. Flag anomalies (loitering, restricted zone, convergence, abrupt motion)
7. Generate AI intelligence report (LLM)
8. Display on operational dashboard

---

## Codebase Structure

```
nautica/
├── ui/                  # Frontend (Vite + Handlebars)
│   ├── components/      # layout, header, sidebar, viewer, metrics, alerts, detections, report, upload
│   └── services/        # API client, event bus, session/analysis services
├── backend/             # FastAPI backend
│   ├── routes/          # health, sessions, upload, detections, anomalies, reports, playback
│   ├── services/        # video, detection (YOLOv8), tracking, anomaly, report
│   ├── models/          # SQLAlchemy models
│   └── schemas/         # Pydantic schemas
├── infra/               # AWS deployment reference docs
├── sample-data/         # Mock JSON data
├── docker-compose.yml
├── Dockerfile           # Frontend container
├── nginx.conf
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, Vanilla JS, Vite, Handlebars |
| Backend | Python, FastAPI, SQLite |
| ML | YOLOv8 (Ultralytics), OpenCV, NumPy, SciPy |
| AI Reports | Google Gemini (configurable) |
| Deployment | Docker, Docker Compose |
| Cloud (ref) | AWS ECS, S3, RDS (documented) |

---

## Design System

| Role | Value |
|------|-------|
| Background | `#05080B` |
| Panel Surface | `#0A1220` |
| Border | `#1E2A3A` |
| Primary Accent | `#19C2C9` |
| Secondary Accent | `#4DA3FF` |
| Text Primary | `#D9E4F2` |
| Text Muted | `#7E8CA0` |
| Success | `#19D27C` |
| Warning | `#F2B94B` |
| Alert | `#EF5A5A` |

Fonts: Inter (UI), JetBrains Mono (data/metrics)

---

## Status

All phases complete. See `COMPLETED.md` for full implementation log.

---

## Future Roadmap

| Version | Codename | Focus |
|---------|----------|-------|
| v2 | Nautica Drift | Marine debris detection + density mapping |
| v3 | Nautica Slick | Oil spill pattern recognition + drift estimation |
| v4 | Nautica Reef | Marine wildlife monitoring |
| v5 | Nautica SOS | Ocean traveler safety + distress detection |
