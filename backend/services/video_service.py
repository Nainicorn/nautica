import shutil
from pathlib import Path

import cv2

from config import settings

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class VideoService:
    """Handles video frame extraction using OpenCV."""

    def extract_frames(self, source_path: str, frames_dir: str) -> dict:
        """Extract frames from a video or copy an image as a single frame.

        Args:
            source_path: Absolute path to the source video/image file.
            frames_dir: Absolute path to the directory where frames will be saved.

        Returns:
            Dict with keys: frame_count, frame_paths
        """
        source = Path(source_path)
        output = Path(frames_dir)
        output.mkdir(parents=True, exist_ok=True)

        ext = source.suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            return self._handle_image(source, output)

        return self._extract_video_frames(source, output)

    def _handle_image(self, source: Path, output: Path) -> dict:
        """Copy a single image as frame_0001.jpg."""
        dest = output / "frame_0001.jpg"

        if source.suffix.lower() == ".jpg" or source.suffix.lower() == ".jpeg":
            shutil.copy2(source, dest)
        else:
            img = cv2.imread(str(source))
            if img is None:
                raise ValueError(f"Cannot read image: {source.name}")
            cv2.imwrite(str(dest), img)

        return {
            "frame_count": 1,
            "frame_paths": [str(dest)],
        }

    def _extract_video_frames(self, source: Path, output: Path) -> dict:
        """Extract every Nth frame from a video file."""
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {source.name}")

        stride = settings.FRAME_STRIDE
        max_frames = settings.MAX_FRAMES
        frame_index = 0
        saved_count = 0
        frame_paths = []

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_index % stride == 0:
                    saved_count += 1
                    frame_name = f"frame_{saved_count:04d}.jpg"
                    frame_path = output / frame_name
                    cv2.imwrite(str(frame_path), frame)
                    frame_paths.append(str(frame_path))

                    if saved_count >= max_frames:
                        break

                frame_index += 1
        finally:
            cap.release()

        if saved_count == 0:
            raise ValueError(f"No frames extracted from video: {source.name}")

        return {
            "frame_count": saved_count,
            "frame_paths": frame_paths,
        }


video_service = VideoService()
