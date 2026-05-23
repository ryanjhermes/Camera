import threading
from io import BytesIO
import cv2
from PIL import Image

class Camera:
    def __init__(self, index=0, jpeg_quality=90):
        self.camera_index = index
        self.jpeg_quality = jpeg_quality
        self._thread_lock = threading.Lock()
        self._capture_device = None

    def _open_capture_device(self):
        if self._capture_device is None or not self._capture_device.isOpened():
            self._capture_device = cv2.VideoCapture(self.camera_index)
            if not self._capture_device.isOpened():
                raise RuntimeError(f"Could not open camera {self.camera_index}")
        return self._capture_device

    def capture_jpeg(self):
        with self._thread_lock:
            capture_device = self._open_capture_device()
            capture_device.grab()
            capture_device.grab()
            read_success, frame_bgr = capture_device.read()
            if not read_success:
                raise RuntimeError("Failed to read frame from camera")

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        jpeg_buffer = BytesIO()
        Image.fromarray(frame_rgb).save(
            jpeg_buffer, format="JPEG", quality=self.jpeg_quality
        )
        return jpeg_buffer.getvalue()

    def release(self):
        with self._thread_lock:
            if self._capture_device is not None:
                self._capture_device.release()
            self._capture_device = None
