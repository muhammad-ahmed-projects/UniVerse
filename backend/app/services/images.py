"""Decode/encode helpers for uploaded images.

Every upload is decoded with OpenCV and re-encoded as JPEG before it is
stored. That rejects anything that isn't really an image, normalizes
PNG/WebP/BMP uploads to one format, and drops EXIF metadata (GPS
location, device info) from photos of people.
"""

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def read_upload(file: UploadFile, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image is larger than {max_bytes // (1024 * 1024)} MB",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Image file is empty")
    return data


def decode(data: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File is not a supported image (use JPEG, PNG, WebP or BMP)",
        )
    return image


def encode_jpeg(image: np.ndarray, max_width: int = 1280, quality: int = 85) -> bytes:
    height, width = image.shape[:2]
    if width > max_width:
        image = cv2.resize(image, (max_width, int(height * max_width / width)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Could not encode image")
    return buf.tobytes()
