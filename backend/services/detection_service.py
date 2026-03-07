class DetectionService:
    """Runs YOLOv8 object detection on individual frames.

    Takes a frame image and returns bounding box detections
    with object type and confidence scores.
    """

    def detect(self, frame_path: str) -> list:
        """Run detection on a single frame.

        Args:
            frame_path: Path to the frame image.

        Returns:
            List of detection dicts with keys:
            object_type, confidence, x, y, width, height.
        """
        raise NotImplementedError("Detection not implemented yet — Step 5")


detection_service = DetectionService()
