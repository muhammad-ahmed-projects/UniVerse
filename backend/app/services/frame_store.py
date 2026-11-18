"""In-memory latest-frame store for the dashboard's live camera view.

AI scripts already read every camera frame, so they publish their
annotated frames (boxes, IDs, names, ROI zone) here via
POST /cameras/{id}/frame, a few times per second. The /ws/stream
WebSocket pushes each camera's newest frame to the dashboards watching it.

Only the latest frame per camera is kept: a slow viewer skips frames
instead of building up a backlog. Like ws_manager, this is single-process
state (fine for the single-instance demo deployment).

All methods run on the event loop (the frame route and the stream
WebSocket are async), so no locking is needed.
"""

import asyncio
import time
from dataclasses import dataclass

# A publisher that hasn't sent a frame for this long has stopped; another
# script may take over the camera, and viewers stop getting its old frame.
STALE_AFTER_SECONDS = 3.0


@dataclass
class Frame:
    jpeg: bytes
    source: str
    priority: int
    seq: int
    received_at: float  # time.monotonic()


class FrameStore:
    def __init__(self) -> None:
        self._frames: dict[int, Frame] = {}
        self._waiters: set[asyncio.Event] = set()

    def publish(self, camera_id: int, jpeg: bytes, source: str, priority: int = 1) -> bool:
        """Store a frame. Returns False if another script owns this camera's
        live view. With several scripts on one IP camera, a higher-priority
        source (a detection script, whose frames carry boxes and names) takes
        over from a lower one (the health monitor's raw frames); between equals
        the first one keeps the view, so the overlays don't flicker.
        """
        now = time.monotonic()
        current = self._frames.get(camera_id)
        if (
            current
            and current.source != source
            and now - current.received_at < STALE_AFTER_SECONDS
            and priority <= current.priority
        ):
            return False
        seq = current.seq + 1 if current else 1
        self._frames[camera_id] = Frame(jpeg=jpeg, source=source, priority=priority, seq=seq, received_at=now)
        for event in self._waiters:
            event.set()
        return True

    def latest(self, camera_id: int) -> Frame | None:
        frame = self._frames.get(camera_id)
        if frame is None or time.monotonic() - frame.received_at >= STALE_AFTER_SECONDS:
            return None
        return frame

    def subscribe(self) -> asyncio.Event:
        """Each viewer gets its own Event (bound to its own loop), set on every publish."""
        event = asyncio.Event()
        self._waiters.add(event)
        return event

    def unsubscribe(self, event: asyncio.Event) -> None:
        self._waiters.discard(event)

    def drop(self, camera_id: int) -> None:
        self._frames.pop(camera_id, None)

    def clear(self) -> None:
        self._frames.clear()


frame_store = FrameStore()
