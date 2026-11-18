"""Server-side face detection + embedding for dashboard face registration.

Uses the same InsightFace buffalo_l model as app/ai/prototypes/
face_recognition.py, so an embedding registered here is directly
comparable to what the recognizer computes from a live frame.

The model (~300 MB, downloaded to ~/.insightface on first use) is loaded
lazily on the first registration, not at API startup, so the API starts
fast and the test suite never needs it (tests override get_face_encoder).
"""

import threading
from dataclasses import dataclass
from typing import Any, Protocol

import cv2
import numpy as np


@dataclass
class DetectedFace:
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 in image pixels
    embedding: list[float]  # L2-normalized, 512 floats
    score: float  # detector confidence 0-1


class FaceEncoder(Protocol):
    def detect(self, image: np.ndarray) -> list[DetectedFace]: ...


class InsightFaceEncoder:
    def __init__(self) -> None:
        self._app: Any = None
        # FaceAnalysis isn't documented as thread-safe, and routes run in a
        # threadpool, so one registration is encoded at a time.
        self._lock = threading.Lock()

    def _load(self) -> Any:
        from insightface.app import FaceAnalysis  # heavy import, deferred until first use

        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        return app

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        with self._lock:
            if self._app is None:
                self._app = self._load()
            faces = self._app.get(image)
            pad_x = pad_y = 0
            if not faces:
                # The detector needs some context around a face: a tightly
                # cropped photo (passport style, face filling the frame) often
                # yields nothing. Retry with a plain border around the image.
                height, width = image.shape[:2]
                pad_y, pad_x = height // 2, width // 2
                padded = cv2.copyMakeBorder(image, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=(0, 0, 0))
                faces = self._app.get(padded)
        height, width = image.shape[:2]
        results = []
        for face in faces:
            x1, y1, x2, y2 = (int(v) for v in face.bbox)
            # Map back to the original image's coordinates.
            x1, x2 = max(x1 - pad_x, 0), min(x2 - pad_x, width)
            y1, y2 = max(y1 - pad_y, 0), min(y2 - pad_y, height)
            results.append(
                DetectedFace(
                    bbox=(x1, y1, x2, y2),
                    embedding=[float(v) for v in face.normed_embedding],
                    score=float(face.det_score),
                )
            )
        return results


_encoder = InsightFaceEncoder()


def get_face_encoder() -> FaceEncoder:
    """FastAPI dependency; tests override it with a fake encoder."""
    return _encoder
