class TrackingService:
    """Multi-object tracking across frames.

    Connects detections across frames and assigns persistent
    track IDs so the same vessel is tracked over time.
    """

    def track(self, detections: list) -> list:
        """Assign track IDs to detections across frames.

        Args:
            detections: List of detection dicts from multiple frames.

        Returns:
            List of track dicts with track_id and detection history.
        """
        raise NotImplementedError("Tracking not implemented yet — Step 7")


tracking_service = TrackingService()
