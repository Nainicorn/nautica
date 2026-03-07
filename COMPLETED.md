# Nautica AI — Completed Log

## Stage 1: Repository Structure
- Initialized git repo
- Created CLAUDE.md with full project context

## Stage 2: Frontend Dashboard Shell
- Created Vite app with custom Handlebars (.hbs) plugin
- Follows same component architecture as punk-app and text-to-3D
- Each component: `.js` (singleton with init/_render/_bindListeners), `.hbs` (template), `.css` (scoped styles)
- CSS naming convention: `__component-name-element`

### Files created:
- `package.json`, `vite.config.js`, `index.html`, `.gitignore`
- `ui/main.js` — entry point, initializes layout
- `ui/styles.css` — global resets, CSS variables (full design system), font imports (Inter + JetBrains Mono)

### Components built (all with static placeholder content):
| Component | Purpose |
|-----------|---------|
| `layout/` | Root flexbox grid — header + sidebar + content (viewer, metrics, alerts, detections, report) |
| `header/` | System bar: NAUTICA brand, "MARITIME INTELLIGENCE SYSTEM" label, live status dot, real-time clock |
| `sidebar/` | Session list with 4 placeholder sessions, "New Analysis" button, collapsible via data-collapsed |
| `viewer/` | Video viewer area with grid background, "NO ACTIVE FEED" empty state, playback controls bar, overlay tags |
| `metrics/` | 2x2 grid of metric cards: Vessels Detected, Active Tracks, Anomalies, Avg Speed (all show "—") |
| `alerts/` | Alert feed with 3 placeholder entries (loitering, restricted zone, convergence) with colored severity dots |
| `detections/` | Detection log table with columns: ID, Type, Confidence, Position, Status — 4 placeholder rows |
| `report/` | Intelligence report with Summary, Anomalies, Recommendation sections — placeholder text |
| `upload/` | Upload modal (hidden by default) with dropzone, file browser button, cancel/submit actions |

### Design system applied:
- Dark intelligence console theme (bg: #05080B, surfaces: #0A1220 / #0F1B2D)
- Accent: teal #19C2C9, secondary: blue #4DA3FF
- Status colors: success #19D27C, warning #F2B94B, alert #EF5A5A
- Fonts: Inter (UI), JetBrains Mono (data/metrics), Material Symbols Outlined (icons)
- Custom scrollbars, border-based panel separation, no shadows

## Stage 3: FastAPI Backend Skeleton
- FastAPI app with CORS, lifespan hooks, tagged routers
- SQLite locally (designed for Postgres swap before deploy)
- Pydantic schemas for clean API contracts
- Sessions fully real in SQLite (seeded from mock JSON on first startup)
- Detections/anomalies/reports served from mock JSON files
- get_db() dependency generator for clean route handlers

### Backend structure:
```
backend/
├── main.py, config.py, database.py
├── models/ — analysis_session, detection, anomaly, report
├── schemas/ — analysis_session, detection, anomaly, report, upload
├── routes/ — health, sessions, upload, detections, anomalies, reports
├── services/ — video, detection, tracking, anomaly, report (stubs)
└── utils/ — mock_loader
```

### Routes implemented:
| Endpoint | Method | Behavior |
|----------|--------|----------|
| /api/health | GET | Returns status + version |
| /api/sessions | GET | Queries SQLite, returns all sessions |
| /api/sessions/{id} | GET | Single session from SQLite, 404 if missing |
| /api/sessions | POST | Persists new session to SQLite |
| /api/upload | POST | Returns mock presigned S3 URL shape |
| /api/sessions/{id}/detections | GET | Returns mock detections from JSON |
| /api/sessions/{id}/anomalies | GET | Returns mock anomalies from JSON |
| /api/sessions/{id}/report | GET | Returns mock report from JSON |

### Mock data:
- `sample-data/mock-json/` — sessions.json, detections.json, anomalies.json, reports.json
- All IDs consistent across files (session_harbor_sweep_04 as primary)
- `sample-data/demo-clips/` and `sample-data/test-images/` — empty with README source recommendations

### Service stubs (NotImplementedError):
- video_service — extract_frames (Step 6)
- detection_service — detect (Step 5)
- tracking_service — track (Step 7)
- anomaly_service — analyze (Step 8)
- report_service — generate (Step 9)

## Stage 4a: Frontend ↔ Backend Read Integration
- Replaced all static placeholder data in frontend components with live API calls
- All panels now fetch from the backend on session selection

### New files:
| File | Purpose |
|------|---------|
| `ui/services/api.js` | Fetch wrapper with `VITE_API_BASE` env support, falls back to `/api` (Vite proxy) |
| `ui/services/events.js` | Lightweight pub/sub event bus (`on`, `off`, `emit`) |
| `ui/services/sessions.js` | `getSessions()`, `getSession(id)` |
| `ui/services/analysis.js` | `getDetections(id)`, `getAnomalies(id)`, `getReport(id)` |

### Components updated:
| Component | Changes |
|-----------|---------|
| `sidebar` | Fetches sessions from API on init, emits `session:selected` on click, dynamic Handlebars template |
| `detections` | Listens for `session:selected`, fetches detections, renders table dynamically with confidence/status classes |
| `alerts` | Listens for `session:selected`, fetches anomalies, renders with severity classes and relative timestamps |
| `report` | Listens for `session:selected`, fetches report (flat object), renders summary/anomalies/recommendation |
| `metrics` | Listens for `session:selected`, fetches detections + anomalies in parallel, derives vessel count, active tracks, anomaly count, avg confidence |

### UI states added:
- All data panels now support: loading, error, empty, and idle states
- CSS for state elements added to sidebar, detections, alerts, and report stylesheets
- Sidebar also has pending and error badge styles

### Event bus events:
- `session:selected` — sidebar → detections, alerts, report, metrics
- `sessions:updated` — triggers sidebar refresh (used by future upload flow)

### Notes:
- Metrics card "Avg Speed" renamed to "Avg Confidence" (no speed data in mock)
- Vite proxy `/api` → `http://localhost:5002` discovered and used (no hardcoded API URL)
- Upload component not modified (deferred to Phase 4b)

## Stage 4b: Upload Pipeline

- Full file upload flow from frontend to backend with progress tracking
- Session creation from UI, file saved to local disk

### Backend changes:
| File | Changes |
|------|---------|
| `routes/upload.py` | Replaced S3 presigned URL stub with multipart file upload endpoint. Validates file type (mp4, mov, avi, jpg, png) and size (200MB max). Saves to `uploads/{session_id}/source/`. Status transitions: `pending` → `uploading` → `uploaded`. |
| `schemas/upload.py` | Simplified UploadResponse: removed S3 fields, added filename + file_size |
| `main.py` | Added `_ensure_uploads_dir()` on startup |

### Frontend changes:
| File | Changes |
|------|---------|
| `services/sessions.js` | Added `createSession(name, fileType)` → `POST /api/sessions` |
| `services/api.js` | Added `uploadFile(sessionId, file, onProgress)` using XMLHttpRequest for progress tracking |
| `components/upload/upload.hbs` | Added hidden file input, file preview area (name, size, remove button), progress bar, error message area |
| `components/upload/upload.js` | Full upload flow: file selection (browse + drag/drop), client-side validation, session creation, file upload with progress, event emission on success, state reset on close |
| `components/upload/upload.css` | Added styles for: drag-active dropzone, file preview info, progress bar + fill animation, error message |
| `components/sidebar/sidebar.js` | Wired "New Analysis" button → opens upload modal. Added `uploaded` status badge ("READY"). Listens for `session:selected` from upload flow to auto-select new session. |

### Upload flow:
1. User clicks "New Analysis" in sidebar → upload modal opens
2. User selects file via browse button or drag/drop
3. Client validates file type and size (200MB max)
4. File preview shows filename + size with remove option
5. User clicks "Start Analysis" → session created → file uploaded with progress bar
6. On success: emits `sessions:updated` (sidebar reloads) + `session:selected` (auto-selects new session)
7. Modal closes, new session visible in sidebar with "READY" badge

### Upload directory structure:
```
uploads/{session_id}/source/{original_filename}
```
Future phases will add: `annotated/` (rendering)

### Events used:
- `sessions:updated` — triggers sidebar session list reload
- `session:selected` — auto-selects newly created session in sidebar

## Stage 5: Video Ingestion + Frame Extraction

- OpenCV-based frame extraction from uploaded video files
- Stride-based extraction (every 10th frame) with 300 frame cap
- Image uploads handled as single-frame input
- Auto-triggered after file upload completes

### Backend changes:
| File | Changes |
|------|---------|
| `requirements.txt` | Added `opencv-python-headless`, `numpy` |
| `config.py` | Added `FRAME_STRIDE=10`, `MAX_FRAMES=300` |
| `services/video_service.py` | Implemented `extract_frames()` — stride-based video extraction via `cv2.VideoCapture`, image copy for jpg/png, saves to `uploads/{session_id}/frames/frame_NNNN.jpg` |
| `models/analysis_session.py` | Added `frame_count` (Integer, nullable) column |
| `schemas/analysis_session.py` | Added `frame_count` to `SessionResponse` |
| `routes/sessions.py` | Added `POST /api/sessions/{session_id}/process` — validates status is `uploaded`, sets `processing`, calls video_service, sets `extracted` on success or `failed` on error |
| `main.py` | Added `_migrate_columns()` to add `frame_count` column to existing DB |

### Frontend changes:
| File | Changes |
|------|---------|
| `services/sessions.js` | Added `processSession(sessionId)` → `POST /api/sessions/{sessionId}/process` |
| `components/upload/upload.js` | After upload success, calls `processSession()` with "Extracting frames..." status text, emits events on completion |
| `components/sidebar/sidebar.js` | Updated badge mapping: `uploaded`→UPLOADED, `processing`→PROCESSING, `extracted`→READY, `uploading`→UPLOADING |

### Status transitions:
`pending` → `uploading` → `uploaded` → `processing` → `extracted` (success) / `failed` (error)

### Directory structure:
```
uploads/{session_id}/
  source/    ← original uploaded file
  frames/    ← extracted frames (frame_0001.jpg, frame_0002.jpg, ...)
```

## Stage 6: YOLO Detection on Frames

- YOLOv8n object detection on extracted frames via `ultralytics`
- MPS (Apple Silicon GPU) acceleration with CPU fallback
- Per-frame detection JSON artifacts saved to disk
- Detection records persisted to SQLite
- Detection API route switched from mock-only to DB-first with mock fallback

### Backend changes:
| File | Changes |
|------|---------|
| `requirements.txt` | Added `ultralytics` |
| `config.py` | Added `YOLO_MODEL`, `YOLO_CONFIDENCE_THRESHOLD`, `YOLO_MAX_DETECTIONS` |
| `services/detection_service.py` | Replaced stub with full YOLOv8 implementation. `DetectionService` loads model once (singleton) on first call, runs on MPS/CPU. `detect()` returns bounding boxes with maritime labels. `run_detection_pipeline()` orchestrates detection across all frames, saves per-frame JSON, persists to DB, manages session status. |
| `routes/sessions.py` | Added `POST /api/sessions/{session_id}/detect` — validates status is `extracted`, runs detection pipeline, returns session + detection_count/frames_processed |
| `routes/detections.py` | Queries Detection model from DB first (ordered by frame_number), falls back to mock JSON for demo sessions. Synthesizes `position` from pixel coords, `status` as "UNTRACKED" for untracked detections. |
| `.gitignore` | Added `.venv/`, `*.pt`, `backend/uploads/` |

### COCO-to-maritime label mapping:
- Class 0 ("person") → "Person"
- Class 8 ("boat") → "Boat"
- All other COCO classes → capitalized COCO name

### Detection pipeline flow:
1. `POST /api/sessions/{id}/detect` validates session status is `extracted`
2. Sets status → `detecting`
3. Iterates sorted `frame_*.jpg` files
4. Runs YOLOv8 inference on each frame
5. Saves detection JSON to `uploads/{session_id}/detections/frame_XXXX.json`
6. Persists Detection records to SQLite (commit per frame)
7. Creates empty `uploads/{session_id}/annotated/` directory (Phase 8 prep)
8. Sets status → `detection_complete`
9. Returns `{detection_count, frames_processed}`

### Status transitions (updated):
`extracted` → `detecting` → `detection_complete` (success) / `failed` (error)

### Directory structure (updated):
```
uploads/{session_id}/
  source/      ← original uploaded file
  frames/      ← extracted frames (frame_0001.jpg, ...)
  detections/  ← per-frame detection JSON (frame_0001.json, ...)
  annotated/   ← empty, prepared for Phase 8
```

### No frontend changes needed:
- Detection table continues to work — same API schema
- `track_id` shows blank (null until Phase 7)
- `position` shows pixel coords instead of GPS
- `status` shows "UNTRACKED" instead of "TRACKING"

## Stage 7: Object Tracking Across Frames

- IoU-based multi-object tracker with Hungarian assignment (scipy)
- Type-aware matching — boats only match boats, persons only match persons
- Confidence gating — detections below TRACKING_MIN_CONFIDENCE (0.3) ignored
- Track lifecycle: active → lost → ended (based on MAX_FRAMES_LOST threshold)
- Persistent track IDs: VES-001, VES-002, etc.
- Tracking artifact saved to `uploads/{session_id}/tracking/tracks.json`

### Algorithm:
1. Iterate frames in sorted order
2. Filter low-confidence detections
3. Group detections and active tracks by object_type
4. Build IoU cost matrix per type, run Hungarian assignment
5. Matched pairs (IoU >= 0.2): update track bbox, reset lost counter
6. Unmatched detections: spawn new tracks
7. Unmatched tracks: increment lost counter, end if > MAX_FRAMES_LOST (5)

### Backend changes:
| File | Changes |
|------|--------|
| `requirements.txt` | Added `scipy` |
| `config.py` | Added `IOU_THRESHOLD=0.2`, `MAX_FRAMES_LOST=5`, `TRACKING_MIN_CONFIDENCE=0.3` |
| `services/tracking_service.py` | Full implementation replacing stub. `TrackingService` class with IoU computation, cost matrix building, Hungarian assignment, track spawning/aging. `run_tracking_pipeline()` orchestrates: loads DB detections, runs tracker, bulk-updates track_id, saves artifact, sets status to `tracking_complete`. |
| `routes/sessions.py` | Added `POST /api/sessions/{session_id}/track` — validates status is `detection_complete`, runs tracking pipeline, returns session + track_count/detections_tracked |
| `routes/detections.py` | Changed detection status label from `"TRACKING"` to `"TRACKED"` when track_id is present |

### Frontend changes:
| File | Changes |
|------|--------|
| `services/sessions.js` | Added `detectSession(sessionId)` and `trackSession(sessionId)` |
| `components/detections/detections.js` | Updated `statusClass()` to handle `"tracked"` for badge styling |

### Tracking artifact schema (`tracks.json`):
```json
{
  "session_id": "...",
  "tracks": [{
    "track_id": "VES-001",
    "object_type": "Boat",
    "state": "active|lost|ended",
    "first_frame": 1,
    "last_frame": 150,
    "detection_count": 45,
    "detections": [{ "frame_number", "detection_id", "bbox", "confidence" }]
  }],
  "summary": {
    "total_tracks", "active_tracks", "lost_tracks", "ended_tracks",
    "total_detections_tracked", "total_detections_skipped", "frames_processed"
  }
}
```

### Status transitions (updated):
`detection_complete` → `tracking` → `tracking_complete` (success) / `failed` (error)

### Directory structure (updated):
```
uploads/{session_id}/
  source/      ← original uploaded file
  frames/      ← extracted frames
  detections/  ← per-frame detection JSON
  tracking/    ← tracks.json artifact (consumed by Phase 8 + 9)
  annotated/   ← empty, prepared for Phase 8
```

### Tracking is triggered separately:
- Not auto-chained in upload flow — called via `POST /api/sessions/{id}/track`
- Frontend has `trackSession()` ready but not wired into upload pipeline yet
- Allows phase-by-phase debugging and control
