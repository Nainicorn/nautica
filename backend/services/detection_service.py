import json
import uuid
import logging
from pathlib import Path

import torch
from ultralytics import YOLO

from config import settings

logger = logging.getLogger(__name__)

# COCO class ID → maritime-friendly label
MARITIME_LABELS = {
    0: "Person",
    5: "Bus",
    7: "Truck",
    8: "Boat",
    14: "Bird",
    33: "Kite",
    36: "Surfboard",
    64: "Potted plant",
}

# Vessel size classification by bounding box area ratio to frame area
VESSEL_SIZE_THRESHOLDS = {
    "Small vessel": 0.01,    # < 1% of frame
    "Medium vessel": 0.05,   # 1-5% of frame
    "Large vessel": 1.0,     # > 5% of frame
}


class DetectionService:
    """Runs YOLOv8 object detection on individual frames.

    Model is loaded once per process and reused across all frames and sessions.
    Uses MPS (Apple Silicon GPU) when available, otherwise falls back to CPU.
    """

    def __init__(self):
        self._model = None
        self._device = None

    @property
    def device(self) -> str:
        if self._device is None:
            if torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            logger.info(f"Detection device: {self._device}")
        return self._device

    @property
    def model(self) -> YOLO:
        if self._model is None:
            self._model = YOLO(settings.YOLO_MODEL)
            self._model.to(self.device)
            logger.info(f"YOLO model loaded: {settings.YOLO_MODEL} on {self.device}")
        return self._model

    def detect(self, frame_path: str) -> list:
        """Run detection on a single frame.

        Args:
            frame_path: Path to the frame image.

        Returns:
            List of detection dicts with keys:
            object_type, confidence, x, y, width, height, vessel_size.
        """
        results = self.model(
            frame_path,
            conf=settings.YOLO_CONFIDENCE_THRESHOLD,
            max_det=settings.YOLO_MAX_DETECTIONS,
            verbose=False,
        )

        detections = []
        for result in results:
            img_h, img_w = result.orig_shape
            frame_area = img_w * img_h

            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                label = MARITIME_LABELS.get(cls_id, cls_name.capitalize())

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                box_w = x2 - x1
                box_h = y2 - y1

                vessel_size = None
                if label == "Boat":
                    area_ratio = (box_w * box_h) / frame_area
                    for size_label, threshold in VESSEL_SIZE_THRESHOLDS.items():
                        if area_ratio < threshold:
                            vessel_size = size_label
                            break

                detections.append({
                    "object_type": label,
                    "confidence": round(float(box.conf[0]), 4),
                    "x": round(x1, 2),
                    "y": round(y1, 2),
                    "width": round(box_w, 2),
                    "height": round(box_h, 2),
                    "vessel_size": vessel_size,
                })

        return detections


detection_service = DetectionService()


def run_detection_pipeline(session_id: str, db) -> dict:
    """Run YOLO detection on all extracted frames for a session.

    Persists Detection records to the database and saves per-frame
    detection JSON files for debugging and visual playback.

    Returns:
        dict with detection_count and frames_processed.
    """
    from models.analysis_session import AnalysisSession
    from models.detection import Detection

    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session.status = "detecting"
    db.commit()

    uploads_dir = settings.uploads_path
    frames_dir = uploads_dir / session_id / "frames"
    detections_dir = uploads_dir / session_id / "detections"
    annotated_dir = uploads_dir / session_id / "annotated"

    # Create output directories
    detections_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)

    # Get sorted frame files
    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    if not frame_files:
        session.status = "failed"
        db.commit()
        raise ValueError(f"No frames found in uploads/{session_id}/frames/")

    total_detections = 0

    for frame_file in frame_files:
        frame_num = int(frame_file.stem.split("_")[1])

        raw_detections = detection_service.detect(str(frame_file))

        # Save per-frame detection JSON
        json_path = detections_dir / f"frame_{frame_num:04d}.json"
        with open(json_path, "w") as f:
            json.dump(raw_detections, f, indent=2)

        # Persist to database
        for det in raw_detections:
            detection = Detection(
                id=f"det_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                track_id=None,
                object_type=det["object_type"],
                confidence=det["confidence"],
                x=det["x"],
                y=det["y"],
                width=det["width"],
                height=det["height"],
                frame_number=frame_num,
                vessel_size=det.get("vessel_size"),
            )
            db.add(detection)
            total_detections += 1

        db.commit()

    logger.info(f"Session {session_id}: {total_detections} detections across {len(frame_files)} frames")

    session.status = "detection_complete"
    db.commit()

    return {
        "detection_count": total_detections,
        "frames_processed": len(frame_files),
    }
