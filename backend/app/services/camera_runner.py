"""Start/stop a camera's AI scripts from the dashboard.

Each analysis still runs as its own process (`python -m
app.ai.prototypes.<script> --camera-id N --source <stream> --headless`),
exactly as an operator would start it in a terminal, so a crash in model
inference can't take the API down. This module only launches those
processes, keeps the last lines of their output for the dashboard, and
stops them.

State is in memory: runners stop when the API stops (lifespan shutdown),
and like ws_manager/frame_store this assumes a single API process.
"""

import logging
import os
import subprocess
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("universe.camera_runner")

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS = ("roi_loitering", "tamper_detection", "face_recognition", "camera_health")
LOG_LINES = 200
STOP_TIMEOUT_SECONDS = 5.0

CommandBuilder = Callable[[str, int, str], list[str]]


def default_command(script: str, camera_id: int, source: str) -> list[str]:
    # An argument list (never a shell string), so a stream URL can't inject commands.
    return [
        sys.executable,
        "-u",  # unbuffered, so the dashboard log updates line by line
        "-m",
        f"app.ai.prototypes.{script}",
        "--source",
        source,
        "--camera-id",
        str(camera_id),
        "--headless",
    ]


def is_webcam(source: str) -> bool:
    """A bare index ("0", "1") is a local USB webcam, which Windows lets only
    one process open at a time; URLs and file paths aren't limited."""
    return source.strip().isdigit()


@dataclass
class ScriptProcess:
    name: str
    process: subprocess.Popen
    started_at: datetime
    stopped_by_user: bool = False

    @property
    def running(self) -> bool:
        return self.process.poll() is None

    @property
    def exit_code(self) -> int | None:
        return self.process.poll()


@dataclass
class CameraRun:
    camera_id: int
    scripts: list[ScriptProcess] = field(default_factory=list)
    log: deque[str] = field(default_factory=lambda: deque(maxlen=LOG_LINES))
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def running(self) -> bool:
        return any(s.running for s in self.scripts)


class RunnerError(Exception):
    pass


class CameraRunner:
    def __init__(self, command_builder: CommandBuilder = default_command) -> None:
        self.command_builder = command_builder
        self._runs: dict[int, CameraRun] = {}
        self._lock = threading.Lock()
        # Called (from a watcher thread) when every script of a camera has
        # exited on its own, e.g. the camera couldn't be opened.
        self.on_all_exited: Callable[[int], None] | None = None

    def get(self, camera_id: int) -> CameraRun | None:
        return self._runs.get(camera_id)

    def all(self) -> list[CameraRun]:
        return list(self._runs.values())

    def start(self, camera_id: int, source: str, scripts: list[str]) -> CameraRun:
        unknown = [s for s in scripts if s not in SCRIPTS]
        if unknown or not scripts:
            raise RunnerError(f"Unknown analysis: {', '.join(unknown) or 'none selected'}")
        if is_webcam(source) and len(scripts) > 1:
            raise RunnerError(
                "This camera is a USB webcam, which only one program can use at a time. Choose one analysis."
            )
        with self._lock:
            current = self._runs.get(camera_id)
            if current and current.running:
                raise RunnerError("Monitoring is already running for this camera. Stop it first.")
            run = CameraRun(camera_id=camera_id)
            self._runs[camera_id] = run

        run.log.append(f"{_now()} starting {', '.join(scripts)} on source {_safe_source(source)}")
        for name in scripts:
            process = subprocess.Popen(
                self.command_builder(name, camera_id, source),
                cwd=BACKEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                # No console window per script on Windows.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            script = ScriptProcess(name=name, process=process, started_at=datetime.now(UTC))
            run.scripts.append(script)
            threading.Thread(target=self._pump_output, args=(run, script), daemon=True).start()
        return run

    def stop(self, camera_id: int) -> CameraRun | None:
        run = self._runs.get(camera_id)
        if run is None:
            return None
        for script in run.scripts:
            if script.running:
                script.stopped_by_user = True
                script.process.terminate()
        deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
        for script in run.scripts:
            try:
                script.process.wait(timeout=max(deadline - time.monotonic(), 0.1))
            except subprocess.TimeoutExpired:
                script.process.kill()
                script.process.wait()
        run.log.append(f"{_now()} stopped from the dashboard")
        return run

    def forget(self, camera_id: int) -> None:
        self.stop(camera_id)
        self._runs.pop(camera_id, None)

    def stop_all(self) -> None:
        for camera_id in list(self._runs):
            self.stop(camera_id)

    def _pump_output(self, run: CameraRun, script: ScriptProcess) -> None:
        """Copies a script's output into the camera's log, then records its exit."""
        assert script.process.stdout is not None
        for line in script.process.stdout:
            line = line.rstrip()
            # InsightFace prints a deprecation warning per frame; it's noise in the dashboard log.
            if line and "FutureWarning" not in line and "tform.estimate" not in line:
                with run.lock:
                    run.log.append(f"[{script.name}] {line}")
        code = script.process.wait()
        if not script.stopped_by_user:
            with run.lock:
                run.log.append(f"{_now()} [{script.name}] exited with code {code}")
            if not run.running and self.on_all_exited is not None:
                try:
                    self.on_all_exited(run.camera_id)
                except Exception:
                    logger.exception("on_all_exited callback failed for camera %s", run.camera_id)


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _safe_source(source: str) -> str:
    """Hide a password in an RTSP URL before it goes into the dashboard log."""
    from urllib.parse import urlsplit

    parts = urlsplit(source)
    if not parts.password:
        return source
    return source.replace(f":{parts.password}@", ":***@")


camera_runner = CameraRunner()
