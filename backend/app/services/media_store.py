"""On-disk storage for evidence snapshots and registered-face thumbnails.

Files live under MEDIA_DIR (env, default backend/media/, gitignored):
    evidence/  -- alert evidence JPEGs (AlertImage.file_name)
    faces/     -- cropped face thumbnails (FaceEmbedding.image_file)

File names are always generated here (random hex + .jpg), never taken
from the client, and every lookup re-checks that pattern, so a stored
name can't be used for path traversal.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

Kind = Literal["evidence", "faces"]

_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "media"
_NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.jpg$")


def media_root() -> Path:
    # Read on every call (not at import) so tests can point it at a temp dir.
    return Path(os.getenv("MEDIA_DIR") or _DEFAULT_ROOT)


def _dir(kind: Kind) -> Path:
    path = media_root() / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(kind: Kind, jpeg: bytes) -> str:
    name = f"{uuid.uuid4().hex}.jpg"
    (_dir(kind) / name).write_bytes(jpeg)
    return name


def path_for(kind: Kind, name: str) -> Path | None:
    """Absolute path of a stored file, or None if the name is invalid or the file is gone."""
    if not _NAME_PATTERN.match(name):
        return None
    path = _dir(kind) / name
    return path if path.is_file() else None


def delete(kind: Kind, name: str | None) -> None:
    if name and _NAME_PATTERN.match(name):
        (_dir(kind) / name).unlink(missing_ok=True)


def list_files(kind: Kind) -> list[Path]:
    return [p for p in _dir(kind).iterdir() if p.is_file() and _NAME_PATTERN.match(p.name)]
