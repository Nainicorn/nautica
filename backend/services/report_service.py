class ReportService:
    """Generates AI intelligence reports from session data.

    Takes structured session data (detections, tracks, anomalies)
    and generates a plain-English intelligence summary using an LLM.
    """

    def generate(self, session_data: dict) -> dict:
        """Generate an intelligence report for a session.

        Args:
            session_data: Dict containing detections, tracks, anomalies.

        Returns:
            Dict with summary, anomalies_text, recommendation.
        """
        raise NotImplementedError("Report generation not implemented yet — Step 9")


report_service = ReportService()
