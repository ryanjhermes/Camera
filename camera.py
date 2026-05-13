"""Webcam capture wrapper around OpenCV."""

from __future__ import annotations

import io
import threading

import cv2
from PIL import Image


class CameraError(RuntimeError):
    pass


class Camera:
    """Thread-safe singleton-ish wrapper around a cv2.VideoCapture device."""

    def __init__(self, index: int = 0, jpeg_quality: int = 90) -> None:
        self.index = index
        self.jpeg_quality = jpeg_quality
        self._lock = threading.Lock()
        self._cap: cv2.VideoCapture | None = None

    def _ensure_open(self) -> cv2.VideoCapture:
        if self._cap is None or not self._cap.isOpened():
            cap = cv2.VideoCapture(self.index)
            if not cap.isOpened():
                raise CameraError(f"Could not open camera index {self.index}")
            self._cap = cap
        return self._cap

    def capture_jpeg(self) -> bytes:
        """Grab a single frame and return JPEG-encoded bytes."""
        with self._lock:
            cap = self._ensure_open()
            # Some USB webcams hand back a stale buffered frame on the first
            # read after being idle. Drain a couple before keeping one.
            for _ in range(2):
                cap.grab()
            ok, frame = cap.read()
            if not ok or frame is None:
                raise CameraError("Failed to read frame from camera")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.jpeg_quality)
        return buf.getvalue()

    def release(self) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                self._cap.release()
            self._cap = None
