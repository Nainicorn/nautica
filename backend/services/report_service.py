import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"


class ReportService:
    """Generates AI intelligence reports from session data."""

    def _build_context(self, detections, anomalies, tracks_data):
        """Aggregate detection, anomaly, and tracking data into structured context."""
        # Detection stats
        total_detections = len(detections)
        track_ids = set()
        object_types = {}
        confidence_sum = 0.0

        for det in detections:
            if det.track_id:
                track_ids.add(det.track_id)
            obj_type = det.object_type or "Unknown"
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
            if det.confidence:
                confidence_sum += det.confidence

        avg_confidence = confidence_sum / total_detections if total_detections else 0

        # Anomaly stats
        anomaly_breakdown = {}
        anomaly_details = []
        for anom in anomalies:
            anom_type = anom.anomaly_type
            anomaly_breakdown[anom_type] = anomaly_breakdown.get(anom_type, 0) + 1
            anomaly_details.append({
                "type": anom_type,
                "severity": anom.severity,
                "description": anom.description,
            })

        # Tracking stats
        tracks_summary = tracks_data.get("summary", {}) if tracks_data else {}
        tracks = tracks_data.get("tracks", []) if tracks_data else []
        track_info = []
        for t in tracks:
            track_info.append({
                "track_id": t["track_id"],
                "object_type": t.get("object_type", "Unknown"),
                "detection_count": t.get("detection_count", 0),
                "state": t.get("state", "unknown"),
            })

        return {
            "total_detections": total_detections,
            "unique_tracks": len(track_ids),
            "avg_confidence": avg_confidence,
            "object_types": object_types,
            "total_anomalies": len(anomalies),
            "anomaly_breakdown": anomaly_breakdown,
            "anomaly_details": anomaly_details,
            "tracks_summary": tracks_summary,
            "track_info": track_info,
        }

    def _build_prompt(self, session_id, context):
        """Build system and user messages for the LLM."""
        system = (
            "You are a senior maritime intelligence analyst generating a detailed operational briefing "
            "from automated vessel detection and tracking data collected via aerial surveillance. "
            "Write in clear, professional operational language. Be thorough and analytical — "
            "reference specific vessel IDs (e.g. VES-001), anomaly types, severity levels, "
            "confidence scores, and frame counts. Provide tactical context and risk assessment. "
            "Write as if briefing a coast guard operations center."
        )

        # Build vessel breakdown
        vessel_lines = []
        for obj_type, count in context["object_types"].items():
            vessel_lines.append(f"  - {obj_type}: {count} detections")

        # Build tracked vessels
        track_lines = []
        for t in context["track_info"]:
            track_lines.append(
                f"  - {t['track_id']} ({t['object_type']}) — "
                f"{t['detection_count']} detections, state: {t['state']}"
            )

        # Build anomaly list
        anomaly_lines = []
        for a in context["anomaly_details"]:
            anomaly_lines.append(f"  - [{a['severity'].upper()}] {a['description']}")

        user = f"""Generate an intelligence report for analysis session {session_id}.

SESSION OVERVIEW:
- Total detections across frames: {context['total_detections']}
- Unique vessels tracked: {context['unique_tracks']}
- Average detection confidence: {context['avg_confidence']:.1%}

VESSEL BREAKDOWN:
{chr(10).join(vessel_lines) if vessel_lines else '  No vessels detected.'}

TRACKED VESSELS:
{chr(10).join(track_lines) if track_lines else '  No tracked vessels.'}

ANOMALIES DETECTED ({context['total_anomalies']}):
{chr(10).join(anomaly_lines) if anomaly_lines else '  No anomalies detected.'}

Write a concise intelligence briefing as continuous prose — do NOT use section headers, bullet points, or markdown formatting. Keep it to 2-3 short paragraphs covering:

1. What was observed — vessel count, types, detection confidence, notable vessel IDs
2. Anomaly analysis — what happened, which vessels, severity. If none, note the area is operationally normal.
3. One sentence on recommended next steps.

Be direct and brief. No filler. Plain paragraphs only — no headers, no bullet points, no markdown."""

        return system, user

    def _call_llm(self, system, user):
        """Call the Gemini API and return the response text."""
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = client.models.generate_content(
            model=settings.LLM_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=2048,
                temperature=0.2,
            ),
        )

        return response.text

    def _stream_llm(self, system, user):
        """Get full response from Gemini, then yield in small chunks for SSE typewriter effect."""
        full_text = self._call_llm(system, user)
        chunk_size = 12
        for i in range(0, len(full_text), chunk_size):
            yield full_text[i:i + chunk_size]

    def _parse_response(self, text):
        """Store the full response as a single summary."""
        return {
            "summary": text.strip(),
            "anomalies_text": None,
            "recommendation": None,
            "raw_text": None,
        }

    def generate(self, session_id, detections, anomalies, tracks_data):
        """Generate an intelligence report for a session.

        Returns:
            Dict with summary, anomalies_text, recommendation, raw_text.
        """
        context = self._build_context(detections, anomalies, tracks_data)
        system, user = self._build_prompt(session_id, context)
        response_text = self._call_llm(system, user)
        parsed = self._parse_response(response_text)
        parsed["stats"] = {
            "detections": context["total_detections"],
            "tracks": context["unique_tracks"],
            "anomalies": context["total_anomalies"],
        }
        return parsed


    def generate_stream(self, session_id, detections, anomalies, tracks_data):
        """Generate report, yielding text chunks as they arrive.

        Yields str chunks. After iteration, call .last_stats for save data.
        """
        context = self._build_context(detections, anomalies, tracks_data)
        system, user = self._build_prompt(session_id, context)
        self._last_stats = {
            "detections": context["total_detections"],
            "tracks": context["unique_tracks"],
            "anomalies": context["total_anomalies"],
        }
        yield from self._stream_llm(system, user)


report_service = ReportService()


def run_report_pipeline(session_id, db):
    """Run AI report generation for a session."""
    from models.analysis_session import AnalysisSession
    from models.detection import Detection
    from models.anomaly import Anomaly
    from models.report import Report

    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    session.status = "generating_report"
    db.commit()

    try:
        # Load tracking artifact
        uploads_dir = settings.uploads_path
        tracks_path = uploads_dir / session_id / "tracking" / "tracks.json"
        tracks_data = None
        if tracks_path.exists():
            with open(tracks_path) as f:
                tracks_data = json.load(f)

        # Query detections and anomalies from DB
        detections = (
            db.query(Detection)
            .filter(Detection.session_id == session_id)
            .order_by(Detection.frame_number)
            .all()
        )
        anomalies = (
            db.query(Anomaly)
            .filter(Anomaly.session_id == session_id)
            .all()
        )

        # Demo mode: no API key configured
        if not settings.GEMINI_API_KEY:
            det_count = len(detections)
            anom_count = len(anomalies)
            track_ids = set(d.track_id for d in detections if d.track_id)
            result = {
                "summary": (
                    f"[DEMO MODE] AI report generation requires a GEMINI_API_KEY. "
                    f"Configure it in your .env file to enable live intelligence reports. "
                    f"Session {session_id} processed {det_count} detections across "
                    f"{len(track_ids)} tracked vessels with {anom_count} anomalies flagged."
                ),
                "anomalies_text": None,
                "recommendation": None,
                "stats": {
                    "detections": det_count,
                    "tracks": len(track_ids),
                    "anomalies": anom_count,
                },
            }
        else:
            # Generate report via LLM
            result = report_service.generate(session_id, detections, anomalies, tracks_data)

        # Clear existing report for this session (re-runnable)
        db.query(Report).filter(Report.session_id == session_id).delete()
        db.commit()

        # Persist to DB
        generated_at = datetime.now(timezone.utc)
        report = Report(
            id=f"rpt_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            summary=result["summary"],
            anomalies_text=result["anomalies_text"],
            recommendation=result["recommendation"],
            generated_at=generated_at,
        )
        db.add(report)
        db.commit()

        # Save artifact
        reports_dir = uploads_dir / session_id / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        artifact = {
            "session_id": session_id,
            "generated_at": generated_at.isoformat(),
            "model": settings.LLM_MODEL,
            "prompt_version": PROMPT_VERSION,
            "stats": result["stats"],
            "summary": result["summary"],
            "anomalies_text": result["anomalies_text"],
            "recommendation": result["recommendation"],
            "raw_text": result.get("raw_text"),
        }
        with open(reports_dir / "report.json", "w") as f:
            json.dump(artifact, f, indent=2)

        logger.info(f"Session {session_id}: report generated with {settings.LLM_MODEL}")

        session.status = "report_complete"
        db.commit()

        return {"report_generated": True}

    except Exception as e:
        session.status = "failed"
        db.commit()
        raise
