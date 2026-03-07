class AnomalyService:
    """Rule-based anomaly detection on tracked objects.

    Analyzes track behavior over time and flags:
    - Loitering (stationary too long)
    - Restricted zone entry
    - Suspicious convergence (multiple vessels approaching same point)
    """

    def analyze(self, tracks: list) -> list:
        """Analyze tracks for anomalous behavior.

        Args:
            tracks: List of track dicts with position history.

        Returns:
            List of anomaly dicts with anomaly_type, severity, description.
        """
        raise NotImplementedError("Anomaly detection not implemented yet — Step 8")


anomaly_service = AnomalyService()
