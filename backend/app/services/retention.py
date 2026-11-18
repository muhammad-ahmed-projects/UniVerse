"""Configurable retention for evidence images (proposal: Security & Privacy).

EVIDENCE_RETENTION_DAYS (env, default 30; 0 = keep forever) -- evidence
snapshots older than this are deleted, both the DB row and the file.
Orphaned files (left on disk after their alert was deleted, e.g. when a
camera is removed and its alerts cascade) are swept too.

Registered-face thumbnails are not time-limited: they live exactly as long
as the person's registration and are deleted with it.
"""

import logging
import os
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.alert import AlertImage
from app.models.person import FaceEmbedding
from app.services import media_store

logger = logging.getLogger("universe.retention")

# Files younger than this are never treated as orphans: an upload may have
# written its file but not yet committed its row.
ORPHAN_GRACE_SECONDS = 3600


def retention_days() -> int:
    try:
        return max(int(os.getenv("EVIDENCE_RETENTION_DAYS", "30")), 0)
    except ValueError:
        return 30


def purge(db: Session, days: int | None = None) -> dict[str, int]:
    days = retention_days() if days is None else days
    expired = 0
    if days > 0:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        rows = db.execute(select(AlertImage.id, AlertImage.file_name).where(AlertImage.captured_at < cutoff)).all()
        if rows:
            db.execute(delete(AlertImage).where(AlertImage.id.in_([r.id for r in rows])))
            db.commit()
            for row in rows:
                media_store.delete("evidence", row.file_name)
        expired = len(rows)

    orphans = 0
    now = time.time()
    known = {
        "evidence": set(db.scalars(select(AlertImage.file_name))),
        "faces": set(db.scalars(select(FaceEmbedding.image_file).where(FaceEmbedding.image_file.is_not(None)))),
    }
    for kind, names in known.items():
        for path in media_store.list_files(kind):  # type: ignore[arg-type]
            if path.name not in names and now - path.stat().st_mtime > ORPHAN_GRACE_SECONDS:
                path.unlink(missing_ok=True)
                orphans += 1

    if expired or orphans:
        logger.info("retention purge: %d expired evidence images, %d orphaned files removed", expired, orphans)
    return {"expired": expired, "orphans": orphans}
