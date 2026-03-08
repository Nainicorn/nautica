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

**What it demonstrates:**
- A real computer vision pipeline (detection → tracking → visual output)
- Object detection + multi-object tracking across video frames
- Rule-based anomaly detection on tracked behavior
- AI-generated intelligence reports from structured data
- A full operational dashboard with live visual playback
- Cloud deployment on AWS

**Future versions** expand into environmental monitoring — debris, oil spills, wildlife, and ocean safety.
**Naming** — may change later, keeping Nautica for now.

---

## How It Works

### 1. Upload footage
Drop in a video or image — drone footage, surveillance clip, aerial photo. File is uploaded from the frontend. In development it is handled locally; in deployment it will be stored in AWS S3 via presigned URL.

### 2. Create session
Backend registers a new analysis session with an ID, timestamp, file reference, and processing status.

**Session statuses:** `pending` → `uploading` → `uploaded` → `processing` → `extracted` → `detecting` → `detection_complete` → `tracking` → `tracking_complete` / `failed`

### 3. Extract frames (video)
OpenCV breaks the video into individual frames for the detection pipeline.

### 4. Run detection
Each frame runs through YOLOv8. The model identifies vessels, boats, people, and floating objects with bounding boxes and confidence scores.

### 5. Track objects across frames
The tracking system connects detections across frames, assigning each object a persistent ID. `VES-001` in frame 1 is the same vessel in frame 200.

### 6. Render annotated visual results
The dashboard plays back footage with detection overlays — bounding boxes, vessel IDs, confidence labels — as the primary output.

### 7. Flag anomalies
Rules fire on tracked behavior data:
- **Loitering** — stationary beyond a threshold
- **Restricted zone entry** — crossed a defined boundary
- **Convergence** — multiple vessels approaching a common point

### 8. Generate intelligence report
An LLM reads the structured session data and produces a plain-English summary with anomaly analysis and recommendations.

### 9. View on dashboard
Dashboard shows: annotated playback, detection table, anomaly alerts, operational metrics, and the intelligence report.

**Primary output hierarchy:**
1. Visual tracked playback (core product)
2. Detection log and anomaly alerts
3. Intelligence report

---

## Codebase Structure

```
nautica-ai/
├── ui/               # frontend dashboard
├── backend/          # API + processing pipeline
├── ml/               # computer vision logic (future)
├── infra/            # AWS + Docker config (future)
├── sample-data/      # mock JSON + demo media placeholders
├── CLAUDE.md
├── COMPLETED.md
```

### ui
Vite + Handlebars, singleton component pattern. Each component: `.hbs`, `.js`, `.css`.

```
ui/
├── main.js
├── styles.css
└── components/
    ├── layout/          # root grid: header + sidebar + content panels
    ├── header/          # system bar (logo, status, clock)
    ├── sidebar/         # session list + new analysis button
    ├── viewer/          # video viewer + detection overlay (primary output)
    ├── metrics/         # 2x2 metric cards
    ├── alerts/          # anomaly alert feed
    ├── detections/      # detection log table
    ├── report/          # AI intelligence report
    └── upload/          # upload modal
```

### backend
FastAPI. Sessions in SQLite (Postgres for deploy). Mock data for detections/anomalies/reports.

```
backend/
├── main.py, config.py, database.py
├── routes/       — health, sessions, upload, detections, anomalies, reports
├── models/       — analysis_session, detection, anomaly, report
├── schemas/      — analysis_session, detection, anomaly, report, upload
├── services/     — video, detection (YOLOv8), tracking (IoU + Hungarian), anomaly, report (stubs)
├── utils/        — mock_loader
└── uploads/      — {session_id}/source/, frames/, detections/, tracking/, annotated/
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────┐
│  Top System Bar                                 │
├──────────┬──────────────────────────┬───────────┤
│          │                          │  Metrics  │
│ Sidebar  │   Video Viewer +         │           │
│   Nav    │   Detection Overlay      │  Alerts   │
│          │   (primary output)       │  Feed     │
├──────────┴──────────────────────────┴───────────┤
│  Detection Table    │    AI Intelligence Report  │
└─────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer          | Technology                    |
|----------------|-------------------------------|
| Frontend       | HTML, CSS, Vanilla JS, Vite   |
| Backend        | Python, FastAPI               |
| ML             | YOLOv8, OpenCV, NumPy         |
| Cloud Storage  | AWS S3                        |
| Compute        | AWS ECS or Lambda             |
| Database       | SQLite (local) / Postgres (deploy) |
| Infrastructure | Docker                        |

---

## Design System

**Style:** High-signal operational intelligence console.

| Role              | Value     |
|-------------------|-----------|
| Background        | `#05080B` |
| Panel Surface     | `#0A1220` |
| Secondary Surface | `#0F1B2D` |
| Border            | `#1E2A3A` |
| Primary Accent    | `#19C2C9` |
| Secondary Accent  | `#4DA3FF` |
| Text Primary      | `#D9E4F2` |
| Text Muted        | `#7E8CA0` |
| Success           | `#19D27C` |
| Warning           | `#F2B94B` |
| Alert             | `#EF5A5A` |

- **Fonts:** Inter (UI), JetBrains Mono (data/metrics)
- Dense, no decoration. Borders over shadows. Teal accent sparingly.

---

## Status

### Completed
1. Repository structure initialized
2. Frontend dashboard shell (Vite + Handlebars, 9 components, full layout with design system)
3. FastAPI backend skeleton (SQLite, models, schemas, 8 routes, service stubs, mock data seeding)
4. Frontend ↔ backend read integration (API service layer, event bus, all panels wired to API)
5. Upload pipeline — session creation + file upload from frontend, progress tracking, sidebar refresh
6. Video ingestion + frame extraction (OpenCV, stride-based, auto-triggered after upload)
7. YOLO detection on frames (YOLOv8m, MPS-accelerated, per-frame JSON artifacts, DB persistence, vessel size classification)
8. Object tracking across frames (IoU + Hungarian assignment, persistent VES-XXX IDs, tracking artifact)
9. Annotated visual playback (frame-by-frame viewer, canvas overlays, FPS-throttled playback, streaming detection log)
10. Anomaly detection on tracked behavior (loitering, restricted zone, convergence, abrupt motion rules)

### Current Phase

---

## Remaining Roadmap

| Phase | Focus |
|-------|-------|
| **11** | Cloud deployment (AWS) |
| **12** | file cleanup, laymans term explanation full project, create readme, make sure everything is prepped to post on linkedin, remove anythin unecessary in claude.md, if/how someone else can demo it themselves |

---

## Future Versions

### Nautica Drift (v2) — Marine Debris Detection
Floating debris, plastic, waste detection + density mapping for environmental reporting.

### Nautica Slick (v3) — Oil Spill Detection
Oil slick pattern recognition from aerial imagery + spill drift trajectory estimation.

### Nautica Reef (v4) — Marine Wildlife Monitoring
Marine animal detection and tracking — dolphins, whales, turtles, sharks. Migration and behavior monitoring.

### Nautica SOS (v5) — Ocean Traveler Safety
Real-time tracking of solo rowers, sailors, and open water cruisers. Distress detection and search-and-rescue alerting.

### Nautica Bunker (v6) - Tsunami & Hurricane detection
