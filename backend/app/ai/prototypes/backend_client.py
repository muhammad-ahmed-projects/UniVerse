"""Shared HTTP client so the AI scripts can read camera_settings, report
camera status, write real alerts, stream live frames, and attach evidence
snapshots through the running FastAPI backend.

Goes through the real REST API (not a direct DB connection) so camera_id
validation, priority validation, and the WebSocket broadcast on new alerts
all happen exactly as they do for any other API client.

Network work that happens every frame (live view) or after an alert
(evidence snapshots, face sightings) runs on a background thread, so a
slow or unreachable backend never stalls the detection loop.

Credentials: pass --api-username/--api-password, or set the
UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD env vars (the seed script's
`ai_service` account). No default credentials are hardcoded here.
"""

import argparse
import logging
import os
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("universe.backend_client")

# Live view is downscaled: it's for a dashboard tile, not a recording.
STREAM_MAX_WIDTH = 640
STREAM_JPEG_QUALITY = 70
EVIDENCE_MAX_WIDTH = 1280
EVIDENCE_JPEG_QUALITY = 85
# After a 409 (another script owns this camera's live view), wait before retrying.
STREAM_CONFLICT_BACKOFF_SECONDS = 2.0
# How long an evidence capture waits for a fresh frame before giving up.
EVIDENCE_FRAME_WAIT_SECONDS = 3.0
# While frames flow, refresh the camera's "online" status and last_seen_at this often.
HEARTBEAT_SECONDS = 10.0


def encode_jpeg(frame: np.ndarray, max_width: int, quality: int) -> bytes | None:
    height, width = frame.shape[:2]
    if width > max_width:
        frame = cv2.resize(frame, (max_width, int(height * max_width / width)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else None


@dataclass
class _EvidenceJob:
    alert_id: int
    due_at: float  # time.monotonic()
    min_seq: int  # only a frame published after the alert counts
    give_up_at: float


class BackendClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        camera_id: int,
        source_name: str,
        stream_fps: float = 5.0,
        stream_priority: int = 1,
        evidence_frames: int = 3,
        evidence_interval: float = 1.0,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.camera_id = camera_id
        self.source_name = source_name
        self.stream_fps = stream_fps
        self.stream_priority = stream_priority
        self.evidence_frames = evidence_frames
        self.evidence_interval = evidence_interval
        self._username = username
        self._password = password
        # requests.Session isn't thread-safe: one for the caller's thread, one for the worker.
        self._session = requests.Session()
        self._worker_session = requests.Session()
        self._token = self._login()

        self._cond = threading.Condition()
        self._latest_frame: np.ndarray | None = None
        self._latest_seq = 0
        self._evidence_jobs: list[_EvidenceJob] = []
        self._tasks: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._stopping = False
        self._last_warning: dict[str, float] = {}
        self._worker = threading.Thread(target=self._run_worker, name="universe-media", daemon=True)
        self._worker.start()

    # ---- HTTP -------------------------------------------------------------

    def _login(self) -> str:
        # Plain requests.post, not a session: either thread may need to re-login.
        resp = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": self._username, "password": self._password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _send(
        self, method: str, path: str, session: requests.Session | None = None, **kwargs: Any
    ) -> requests.Response:
        """Authenticated request. JWTs expire (8h), and these scripts are meant
        to run unattended for longer than that, so a 401 triggers one re-login
        and retry instead of failing every call from then on.
        """
        session = session or self._session
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        resp = session.request(method, url, headers={**headers, **self._headers()}, timeout=self.timeout, **kwargs)
        if resp.status_code == 401:
            self._token = self._login()
            resp = session.request(method, url, headers={**headers, **self._headers()}, timeout=self.timeout, **kwargs)
        return resp

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._send(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def _warn(self, key: str, message: str, *args: Any) -> None:
        """Log a warning at most every 30s per key, so a down backend doesn't flood the console."""
        now = time.monotonic()
        if now - self._last_warning.get(key, float("-inf")) >= 30:
            self._last_warning[key] = now
            logger.warning(message, *args)

    # ---- Calls made from the detection loop -------------------------------

    def get_camera_settings(self) -> dict:
        # Called once at startup; let failures propagate so a misconfigured
        # camera_id or backend URL stops the script immediately.
        return self._request("GET", f"/cameras/{self.camera_id}/settings")

    def get_face_embeddings(self) -> list[dict]:
        resp = self._send("GET", "/face-embeddings")
        if resp.status_code == 403:
            raise PermissionError(
                f"user '{self._username}' may not read face embeddings: run face recognition with the "
                "ai_service account (UNIVERSE_API_USERNAME=ai_service in backend/.env) or an admin account"
            )
        resp.raise_for_status()
        return resp.json()

    def heartbeat(self, status: str) -> dict | None:
        try:
            return self._request("POST", f"/cameras/{self.camera_id}/heartbeat", json={"status": status})
        except requests.RequestException as exc:
            self._warn("heartbeat", "heartbeat for camera %s failed: %s", self.camera_id, exc)
            return None

    def post_alert(
        self,
        alert_type: str,
        priority: str,
        message: str,
        extra_data: dict | None = None,
        evidence: bool = True,
    ) -> dict | None:
        """Raise an alert. With evidence=True, the next `evidence_frames` frames
        passed to publish_frame (one every `evidence_interval` seconds) are
        attached to it as evidence images.
        """
        # Mid-loop call: a backend restart or network blip must not kill the
        # detection loop, so log and carry on (the console print still records it).
        try:
            alert = self._request(
                "POST",
                "/alerts",
                json={
                    "camera_id": self.camera_id,
                    "alert_type": alert_type,
                    "priority": priority,
                    "message": message,
                    "extra_data": extra_data,
                },
            )
        except requests.RequestException as exc:
            logger.warning("posting %s alert for camera %s failed: %s", alert_type, self.camera_id, exc)
            return None
        if evidence and self.evidence_frames > 0:
            self._schedule_evidence(alert["id"])
        return alert

    def publish_frame(self, frame: np.ndarray) -> None:
        """Hand the latest annotated frame to the worker (live view + evidence).
        Cheap: stores a reference, no copy or encoding on the caller's thread.
        Pass a frame you won't draw on afterwards."""
        with self._cond:
            self._latest_frame = frame
            self._latest_seq += 1
            self._cond.notify()

    def report_sighting(self, person_id: int, similarity: float) -> None:
        def task() -> None:
            resp = self._send(
                "POST",
                f"/people/{person_id}/sightings",
                session=self._worker_session,
                json={"camera_id": self.camera_id, "similarity": round(min(max(similarity, 0.0), 1.0), 4)},
            )
            resp.raise_for_status()

        self._tasks.put(task)
        with self._cond:
            self._cond.notify()

    def close(self) -> None:
        """Finish pending evidence uploads (bounded), then stop the worker."""
        with self._cond:
            self._stopping = True
            self._cond.notify()
        self._worker.join(timeout=EVIDENCE_FRAME_WAIT_SECONDS + self.evidence_frames * self.evidence_interval + 5)

    # ---- Background worker ------------------------------------------------

    def _schedule_evidence(self, alert_id: int) -> None:
        now = time.monotonic()
        with self._cond:
            min_seq = self._latest_seq + 1
            for i in range(self.evidence_frames):
                due = now + i * self.evidence_interval
                self._evidence_jobs.append(
                    _EvidenceJob(alert_id, due, min_seq, give_up_at=due + EVIDENCE_FRAME_WAIT_SECONDS)
                )
            self._cond.notify()

    def _run_worker(self) -> None:
        last_streamed_seq = 0
        next_stream_at = 0.0
        # alert_id -> seq of its last evidence image, so a stalled feed doesn't
        # attach the same frame several times.
        evidence_seq: dict[int, int] = {}
        # Frames arriving means the camera works: every script (not only
        # camera_health) keeps its status "online" while it reads frames.
        last_heartbeat = float("-inf")
        heartbeat_seq = 0
        while True:
            with self._cond:
                self._cond.wait(timeout=0.05)
                now = time.monotonic()
                frame, seq = self._latest_frame, self._latest_seq
                due_jobs = [
                    j for j in self._evidence_jobs if now >= j.due_at and (seq >= j.min_seq or now >= j.give_up_at)
                ]
                for job in due_jobs:
                    self._evidence_jobs.remove(job)
                done = self._stopping and not self._evidence_jobs and self._tasks.empty()

            for job in due_jobs:
                if frame is not None and seq >= job.min_seq and evidence_seq.get(job.alert_id) != seq:
                    evidence_seq[job.alert_id] = seq
                    self._upload_evidence(job.alert_id, frame)

            while not self._tasks.empty():
                try:
                    self._tasks.get_nowait()()
                except requests.RequestException as exc:
                    self._warn("task", "background request failed: %s", exc)

            if (
                not self._stopping
                and self.stream_fps > 0
                and frame is not None
                and seq != last_streamed_seq
                and now >= next_stream_at
            ):
                last_streamed_seq = seq
                next_stream_at = now + 1.0 / self.stream_fps
                if not self._stream_frame(frame):
                    next_stream_at = now + STREAM_CONFLICT_BACKOFF_SECONDS

            if not self._stopping and seq != heartbeat_seq and now - last_heartbeat >= HEARTBEAT_SECONDS:
                heartbeat_seq, last_heartbeat = seq, now
                try:
                    self._send(
                        "POST",
                        f"/cameras/{self.camera_id}/heartbeat",
                        session=self._worker_session,
                        json={"status": "online"},
                    ).raise_for_status()
                except requests.RequestException as exc:
                    self._warn("heartbeat", "heartbeat for camera %s failed: %s", self.camera_id, exc)

            if done:
                return

    def _stream_frame(self, frame: np.ndarray) -> bool:
        jpeg = encode_jpeg(frame, STREAM_MAX_WIDTH, STREAM_JPEG_QUALITY)
        if jpeg is None:
            return True
        try:
            resp = self._send(
                "POST",
                f"/cameras/{self.camera_id}/frame",
                session=self._worker_session,
                params={"source": self.source_name, "priority": self.stream_priority},
                data=jpeg,
                headers={"Content-Type": "image/jpeg"},
            )
        except requests.RequestException as exc:
            self._warn("stream", "live view frame for camera %s failed: %s", self.camera_id, exc)
            return True
        if resp.status_code == 409:
            self._warn("stream-409", "camera %s's live view is coming from another script", self.camera_id)
            return False
        if not resp.ok:
            self._warn(
                "stream", "live view frame for camera %s rejected: %s %s", self.camera_id, resp.status_code, resp.text
            )
        return True

    def _upload_evidence(self, alert_id: int, frame: np.ndarray) -> None:
        jpeg = encode_jpeg(frame, EVIDENCE_MAX_WIDTH, EVIDENCE_JPEG_QUALITY)
        if jpeg is None:
            return
        try:
            resp = self._send(
                "POST",
                f"/alerts/{alert_id}/images",
                session=self._worker_session,
                files={"file": ("evidence.jpg", jpeg, "image/jpeg")},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            self._warn("evidence", "evidence image for alert %s failed: %s", alert_id, exc)


def add_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--camera-id",
        type=int,
        default=None,
        help="If set, read thresholds from camera_settings, write real alerts, and stream to the dashboard",
    )
    # 127.0.0.1, not localhost: on this Windows setup "localhost" resolves to
    # ::1 first, which times out (~2s) before falling back to IPv4.
    parser.add_argument(
        "--api-base", default=os.getenv("UNIVERSE_API_BASE", "http://127.0.0.1:8000"), help="Backend base URL"
    )
    parser.add_argument("--api-username", default=os.getenv("UNIVERSE_API_USERNAME"))
    parser.add_argument("--api-password", default=os.getenv("UNIVERSE_API_PASSWORD"))
    parser.add_argument(
        "--stream-fps", type=float, default=5.0, help="Live-view frames per second sent to the dashboard (0 = off)"
    )
    parser.add_argument(
        "--evidence-frames", type=int, default=3, help="Evidence images attached to each alert (0 = none)"
    )
    parser.add_argument(
        "--evidence-interval", type=float, default=1.0, help="Seconds between an alert's evidence images"
    )


def build_client(args: argparse.Namespace, source_name: str, stream_priority: int = 1) -> BackendClient | None:
    """`source_name` identifies the script in the live view (e.g. "roi_loitering").
    `stream_priority`: detection scripts 1; the health monitor 0, so a detection
    script's annotated frames win the camera's live view."""
    if args.camera_id is None:
        return None
    if not args.api_username or not args.api_password:
        raise SystemExit(
            "--camera-id given but no credentials: pass --api-username/--api-password "
            "or set UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD"
        )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return BackendClient(
        args.api_base,
        args.api_username,
        args.api_password,
        camera_id=args.camera_id,
        source_name=source_name,
        stream_fps=max(args.stream_fps, 0.0),
        stream_priority=stream_priority,
        evidence_frames=max(args.evidence_frames, 0),
        evidence_interval=max(args.evidence_interval, 0.0),
    )
