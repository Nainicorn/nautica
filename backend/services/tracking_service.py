import json
import logging
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.optimize import linear_sum_assignment

from config import settings

logger = logging.getLogger(__name__)


class TrackingService:
    """IoU-based multi-object tracker with Hungarian assignment.

    Links detections across frames and assigns persistent track IDs
    (VES-001, VES-002, ...) so the same vessel is identified over time.
    """

    def __init__(self):
        self._next_id = 1
        self._tracks = []

    def _assign_track_id(self) -> str:
        track_id = f"VES-{self._next_id:03d}"
        self._next_id += 1
        return track_id

    @staticmethod
    def _compute_iou(box_a, box_b) -> float:
        """Compute IoU between two (x, y, w, h) bounding boxes."""
        ax1, ay1 = box_a[0], box_a[1]
        ax2, ay2 = ax1 + box_a[2], ay1 + box_a[3]
        bx1, by1 = box_b[0], box_b[1]
        bx2, by2 = bx1 + box_b[2], by1 + box_b[3]

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0

        area_a = box_a[2] * box_a[3]
        area_b = box_b[2] * box_b[3]
        union = area_a + area_b - inter

        return inter / union if union > 0 else 0.0

    def track(self, detections_by_frame: dict) -> tuple:
        """Run tracking across all frames.

        Args:
            detections_by_frame: {frame_number: [detection_dicts]}
                Each detection dict has: id, object_type, confidence, x, y, width, height

        Returns:
            (assignment_map, tracks_data)
            - assignment_map: {detection_id: track_id}
            - tracks_data: list of track dicts for artifact output
        """
        assignment_map = {}
        sorted_frames = sorted(detections_by_frame.keys())

        for frame_num in sorted_frames:
            frame_dets = [
                d for d in detections_by_frame[frame_num]
                if d["confidence"] >= settings.TRACKING_MIN_CONFIDENCE
            ]

            # Get matchable tracks (active or lost, not ended)
            matchable = [t for t in self._tracks if t["state"] != "ended"]

            if not matchable or not frame_dets:
                # No matching possible — age unmatched tracks, spawn new ones
                for t in matchable:
                    t["frames_lost"] += 1
                    if t["frames_lost"] > settings.MAX_FRAMES_LOST:
                        t["state"] = "ended"
                for d in frame_dets:
                    self._spawn_track(d, frame_num, assignment_map)
                continue

            # Group by object_type for type-aware matching
            det_types = defaultdict(list)
            for i, d in enumerate(frame_dets):
                det_types[d["object_type"]].append((i, d))

            track_types = defaultdict(list)
            for j, t in enumerate(matchable):
                track_types[t["object_type"]].append((j, t))

            matched_det_indices = set()
            matched_track_indices = set()

            # Run Hungarian per object type
            for obj_type in set(list(det_types.keys()) + list(track_types.keys())):
                dets_of_type = det_types.get(obj_type, [])
                tracks_of_type = track_types.get(obj_type, [])

                if not dets_of_type or not tracks_of_type:
                    continue

                n_dets = len(dets_of_type)
                n_tracks = len(tracks_of_type)
                cost_matrix = np.ones((n_dets, n_tracks))

                for di, (_, det) in enumerate(dets_of_type):
                    det_box = (det["x"], det["y"], det["width"], det["height"])
                    for ti, (_, trk) in enumerate(tracks_of_type):
                        iou = self._compute_iou(det_box, trk["bbox"])
                        cost_matrix[di, ti] = 1.0 - iou

                row_ind, col_ind = linear_sum_assignment(cost_matrix)

                for r, c in zip(row_ind, col_ind):
                    iou = 1.0 - cost_matrix[r, c]
                    if iou >= settings.IOU_THRESHOLD:
                        det_global_idx, det = dets_of_type[r]
                        trk_global_idx, trk = tracks_of_type[c]

                        # Update track
                        trk["bbox"] = (det["x"], det["y"], det["width"], det["height"])
                        trk["last_frame"] = frame_num
                        trk["frames_lost"] = 0
                        trk["state"] = "active"
                        trk["detections"].append({
                            "frame_number": frame_num,
                            "detection_id": det["id"],
                            "bbox": {"x": det["x"], "y": det["y"], "width": det["width"], "height": det["height"]},
                            "confidence": det["confidence"],
                        })
                        assignment_map[det["id"]] = trk["track_id"]

                        matched_det_indices.add(det_global_idx)
                        matched_track_indices.add(trk_global_idx)

            # Age unmatched tracks
            for j, t in enumerate(matchable):
                if j not in matched_track_indices:
                    t["frames_lost"] += 1
                    if t["frames_lost"] > settings.MAX_FRAMES_LOST:
                        t["state"] = "ended"
                    elif t["state"] == "active":
                        t["state"] = "lost"

            # Spawn new tracks for unmatched detections
            for i, d in enumerate(frame_dets):
                if i not in matched_det_indices:
                    self._spawn_track(d, frame_num, assignment_map)

        # Build output track data
        tracks_data = []
        for t in self._tracks:
            tracks_data.append({
                "track_id": t["track_id"],
                "object_type": t["object_type"],
                "state": t["state"],
                "first_frame": t["first_frame"],
                "last_frame": t["last_frame"],
                "detection_count": len(t["detections"]),
                "detections": t["detections"],
            })

        return assignment_map, tracks_data

    def _spawn_track(self, detection: dict, frame_num: int, assignment_map: dict):
        track_id = self._assign_track_id()
        self._tracks.append({
            "track_id": track_id,
            "object_type": detection["object_type"],
            "bbox": (detection["x"], detection["y"], detection["width"], detection["height"]),
            "first_frame": frame_num,
            "last_frame": frame_num,
            "state": "active",
            "frames_lost": 0,
            "detections": [{
                "frame_number": frame_num,
                "detection_id": detection["id"],
                "bbox": {"x": detection["x"], "y": detection["y"], "width": detection["width"], "height": detection["height"]},
                "confidence": detection["confidence"],
            }],
        })
        assignment_map[detection["id"]] = track_id


def run_tracking_pipeline(session_id: str, db) -> dict:
    """Run object tracking on all detections for a session.

    Groups detections by frame, runs IoU-based tracking, updates
    track_id on each Detection record, and saves a tracking artifact.

    Returns:
        dict with track_count and detections_tracked.
    """
    from models.analysis_session import AnalysisSession
    from models.detection import Detection

    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session.status = "tracking"
    db.commit()

    try:
        # Load all detections grouped by frame
        db_detections = (
            db.query(Detection)
            .filter(Detection.session_id == session_id)
            .order_by(Detection.frame_number)
            .all()
        )

        if not db_detections:
            session.status = "failed"
            db.commit()
            raise ValueError(f"No detections found for session {session_id}")

        detections_by_frame = defaultdict(list)
        for d in db_detections:
            detections_by_frame[d.frame_number].append({
                "id": d.id,
                "object_type": d.object_type,
                "confidence": d.confidence,
                "x": d.x,
                "y": d.y,
                "width": d.width,
                "height": d.height,
            })

        # Run tracker
        tracker = TrackingService()
        assignment_map, tracks_data = tracker.track(detections_by_frame)

        # Bulk-update track_id on Detection records
        det_lookup = {d.id: d for d in db_detections}
        for det_id, track_id in assignment_map.items():
            if det_id in det_lookup:
                det_lookup[det_id].track_id = track_id
        db.commit()

        # Save tracking artifact
        uploads_dir = settings.uploads_path
        tracking_dir = uploads_dir / session_id / "tracking"
        tracking_dir.mkdir(parents=True, exist_ok=True)

        active_count = sum(1 for t in tracks_data if t["state"] == "active")
        lost_count = sum(1 for t in tracks_data if t["state"] == "lost")
        ended_count = sum(1 for t in tracks_data if t["state"] == "ended")

        artifact = {
            "session_id": session_id,
            "tracks": tracks_data,
            "summary": {
                "total_tracks": len(tracks_data),
                "active_tracks": active_count,
                "lost_tracks": lost_count,
                "ended_tracks": ended_count,
                "total_detections_tracked": len(assignment_map),
                "total_detections_skipped": len(db_detections) - len(assignment_map),
                "frames_processed": len(detections_by_frame),
            },
        }

        with open(tracking_dir / "tracks.json", "w") as f:
            json.dump(artifact, f, indent=2)

        logger.info(
            f"Session {session_id}: {len(tracks_data)} tracks, "
            f"{len(assignment_map)} detections tracked across {len(detections_by_frame)} frames"
        )

        session.status = "tracking_complete"
        db.commit()

        return {
            "track_count": len(tracks_data),
            "detections_tracked": len(assignment_map),
        }

    except Exception:
        session.status = "failed"
        db.commit()
        raise
