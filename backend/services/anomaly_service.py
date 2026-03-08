import json
import uuid
import math
import logging
from pathlib import Path
from collections import defaultdict

from config import settings

logger = logging.getLogger(__name__)


class AnomalyService:
    """Rule-based anomaly detection on tracked vessel behavior."""

    def analyze(self, tracks, session_id):
        """Analyze tracks for anomalous behavior.

        Args:
            tracks: List of track dicts from tracks.json artifact.
            session_id: The session ID for context.

        Returns:
            List of anomaly dicts.
        """
        anomalies = []
        anomalies.extend(self._check_loitering(tracks))
        anomalies.extend(self._check_restricted_zones(tracks))
        anomalies.extend(self._check_convergence(tracks))
        anomalies.extend(self._check_abrupt_motion(tracks))
        return anomalies

    def _center(self, det):
        bbox = det["bbox"]
        return (bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)

    def _distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def _check_loitering(self, tracks):
        anomalies = []
        for track in tracks:
            if track.get("object_type") != "Boat":
                continue
            dets = track.get("detections", [])
            if len(dets) < settings.LOITERING_MIN_FRAMES:
                continue

            centers = [self._center(d) for d in dets]
            first = centers[0]
            max_disp = max(self._distance(first, c) for c in centers)

            if max_disp < settings.LOITERING_MAX_DISPLACEMENT_PX:
                duration = len(dets)
                severity = "critical" if duration >= settings.LOITERING_CRITICAL_FRAMES else "warning"
                mid_idx = len(dets) // 2
                frame_num = dets[mid_idx]["frame_number"]

                anomalies.append({
                    "anomaly_type": "loitering",
                    "severity": severity,
                    "description": f"Loitering detected — {track['track_id']} stationary for {duration} frames",
                    "track_ids": [track["track_id"]],
                    "frame_number": frame_num,
                    "meta": f"Track ID: {track['track_id']} · Duration: {duration} frames · Displacement: {max_disp:.1f}px",
                })
        return anomalies

    def _check_restricted_zones(self, tracks):
        zones = settings.RESTRICTED_ZONES
        if not zones:
            return []

        anomalies = []
        for track in tracks:
            if track.get("object_type") != "Boat":
                continue
            dets = track.get("detections", [])
            for zone in zones:
                zx, zy = zone["x"], zone["y"]
                zw, zh = zone["width"], zone["height"]

                for det in dets:
                    cx, cy = self._center(det)
                    if zx <= cx <= zx + zw and zy <= cy <= zy + zh:
                        anomalies.append({
                            "anomaly_type": "restricted_zone",
                            "severity": "critical",
                            "description": f"Restricted zone entry — {track['track_id']} entered {zone['name']}",
                            "track_ids": [track["track_id"]],
                            "frame_number": det["frame_number"],
                            "meta": f"Track ID: {track['track_id']} · Zone: {zone['name']} · Frame: {det['frame_number']}",
                        })
                        break  # one flag per track per zone
        return anomalies

    def _check_convergence(self, tracks):
        # Build per-frame lookup of active vessel centers
        frame_vessels = defaultdict(list)
        for track in tracks:
            if track.get("object_type") != "Boat":
                continue
            for det in track.get("detections", []):
                cx, cy = self._center(det)
                frame_vessels[det["frame_number"]].append({
                    "track_id": track["track_id"],
                    "cx": cx,
                    "cy": cy,
                })

        # For each frame, find connected components of nearby vessels
        group_frames = defaultdict(list)  # frozenset(track_ids) -> [frame_numbers]

        for frame_num in sorted(frame_vessels.keys()):
            vessels = frame_vessels[frame_num]
            if len(vessels) < settings.CONVERGENCE_MIN_VESSELS:
                continue

            # Build adjacency for connected-component clustering
            n = len(vessels)
            adj = defaultdict(set)
            for i in range(n):
                for j in range(i + 1, n):
                    dist = self._distance(
                        (vessels[i]["cx"], vessels[i]["cy"]),
                        (vessels[j]["cx"], vessels[j]["cy"]),
                    )
                    if dist < settings.CONVERGENCE_DISTANCE_PX:
                        adj[i].add(j)
                        adj[j].add(i)

            # Find connected components via BFS
            visited = set()
            for start in range(n):
                if start in visited:
                    continue
                if start not in adj:
                    continue
                component = set()
                queue = [start]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    component.add(node)
                    queue.extend(adj[node] - visited)

                if len(component) >= settings.CONVERGENCE_MIN_VESSELS:
                    group_key = frozenset(vessels[i]["track_id"] for i in component)
                    group_frames[group_key].append(frame_num)

        # Filter groups that persist for enough frames and compute min gap
        anomalies = []
        for group_key, frames in group_frames.items():
            # Find longest consecutive run
            frames_sorted = sorted(frames)
            max_run = 1
            current_run = 1
            run_start = frames_sorted[0]
            best_start = run_start
            for i in range(1, len(frames_sorted)):
                if frames_sorted[i] == frames_sorted[i - 1] + 1:
                    current_run += 1
                    if current_run > max_run:
                        max_run = current_run
                        best_start = run_start
                else:
                    current_run = 1
                    run_start = frames_sorted[i]

            if max_run < settings.CONVERGENCE_MIN_FRAMES:
                continue

            track_ids = sorted(group_key)
            vessel_count = len(track_ids)
            severity = "warning" if vessel_count >= 3 else "info"
            end_frame = best_start + max_run - 1

            anomalies.append({
                "anomaly_type": "convergence",
                "severity": severity,
                "description": f"Vessel convergence — {', '.join(track_ids)} in close proximity",
                "track_ids": track_ids,
                "frame_number": best_start,
                "meta": f"Vessels: {', '.join(track_ids)} · Frames: {best_start}-{end_frame}",
            })

        return anomalies

    def _check_abrupt_motion(self, tracks):
        anomalies = []
        for track in tracks:
            dets = track.get("detections", [])
            if len(dets) < 2:
                continue

            jumps = []
            max_disp = 0
            max_frame = dets[0]["frame_number"]

            for i in range(1, len(dets)):
                c_prev = self._center(dets[i - 1])
                c_curr = self._center(dets[i])
                disp = self._distance(c_prev, c_curr)

                if disp > settings.ABRUPT_MOTION_PX_PER_FRAME:
                    jumps.append((dets[i]["frame_number"], disp))
                    if disp > max_disp:
                        max_disp = disp
                        max_frame = dets[i]["frame_number"]

            if jumps:
                severity = "warning" if len(jumps) > 1 else "info"
                anomalies.append({
                    "anomaly_type": "abrupt_motion",
                    "severity": severity,
                    "description": f"Abrupt motion — {track['track_id']} position jump detected",
                    "track_ids": [track["track_id"]],
                    "frame_number": max_frame,
                    "meta": f"Track ID: {track['track_id']} · Max displacement: {max_disp:.1f}px · Frame: {max_frame}",
                })

        return anomalies


anomaly_service = AnomalyService()


def run_anomaly_pipeline(session_id, db):
    """Run anomaly detection on tracked data for a session."""
    from models.analysis_session import AnalysisSession
    from models.anomaly import Anomaly

    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session.status = "anomaly_detection"
    db.commit()

    uploads_dir = settings.uploads_path
    tracks_path = uploads_dir / session_id / "tracking" / "tracks.json"

    if not tracks_path.exists():
        session.status = "failed"
        db.commit()
        raise ValueError(f"No tracking artifact found: {tracks_path}")

    with open(tracks_path) as f:
        tracks_data = json.load(f)

    tracks = tracks_data.get("tracks", [])
    results = anomaly_service.analyze(tracks, session_id)

    # Clear existing anomalies for this session (re-runnable)
    db.query(Anomaly).filter(Anomaly.session_id == session_id).delete()
    db.commit()

    # Persist anomalies to DB
    for anom in results:
        anomaly = Anomaly(
            id=f"anom_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            anomaly_type=anom["anomaly_type"],
            severity=anom["severity"],
            description=anom["description"],
            track_ids=json.dumps(anom["track_ids"]),
            meta=anom.get("meta"),
            frame_number=anom["frame_number"],
        )
        db.add(anomaly)
    db.commit()

    # Save artifact to disk
    anomalies_dir = uploads_dir / session_id / "anomalies"
    anomalies_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = anomalies_dir / "anomalies.json"
    with open(artifact_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Session {session_id}: {len(results)} anomalies detected")

    session.status = "anomaly_complete"
    db.commit()

    return {"anomaly_count": len(results)}
