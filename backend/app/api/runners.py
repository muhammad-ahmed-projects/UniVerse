"""Start/stop a camera's AI scripts from the dashboard (services/camera_runner.py)."""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import SessionLocal, get_db
from app.models.camera import Camera, CameraStatus
from app.models.user import User, UserRole
from app.schemas.runner import RunnerOut, RunnerScriptOut, RunnerStart
from app.services.audit import Auditor, get_auditor
from app.services.camera_runner import CameraRun, RunnerError, camera_runner, is_webcam
from app.services.ws_manager import manager

router = APIRouter(prefix="/cameras", tags=["monitoring"])
list_router = APIRouter(prefix="/camera-runners", tags=["monitoring"])

admin_only = Depends(require_role(UserRole.ADMIN))

# Set at startup (main.py lifespan) so watcher threads can broadcast on the API's event loop.
event_loop: asyncio.AbstractEventLoop | None = None


def _to_out(camera: Camera, run: CameraRun | None) -> RunnerOut:
    scripts = []
    log: list[str] = []
    if run is not None:
        with run.lock:
            log = list(run.log)
        scripts = [
            RunnerScriptOut(
                name=s.name,
                pid=s.process.pid,
                running=s.running,
                exit_code=s.exit_code,
                stopped_by_user=s.stopped_by_user,
                started_at=s.started_at,
            )
            for s in run.scripts
        ]
    return RunnerOut(
        camera_id=camera.id,
        running=run is not None and run.running,
        is_webcam=is_webcam(camera.stream_source),
        scripts=scripts,
        log=log,
    )


def _get_camera_or_404(camera_id: int, db: Session) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


def _set_status(camera_id: int, new_status: CameraStatus) -> dict | None:
    """Update a camera's status; returns the broadcast message if it changed."""
    with SessionLocal() as db:
        camera = db.get(Camera, camera_id)
        if camera is None or camera.status == new_status:
            return None
        camera.status = new_status
        db.commit()
        return {"type": "camera_status", "camera_id": camera_id, "status": new_status.value}


def _runner_message(camera_id: int, running: bool) -> dict:
    return {"type": "camera_runner", "camera_id": camera_id, "running": running}


def on_all_scripts_exited(camera_id: int) -> None:
    """Runs on a watcher thread when a camera's scripts all stopped on their
    own (camera unreachable, crash, video file ended): the feed is gone, so
    the camera is offline. Dashboards are told on the API's event loop."""
    messages = [_runner_message(camera_id, running=False)]
    status_message = _set_status(camera_id, CameraStatus.OFFLINE)
    if status_message:
        messages.append(status_message)
    if event_loop is not None and not event_loop.is_closed():
        for message in messages:
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), event_loop)


camera_runner.on_all_exited = on_all_scripts_exited


@list_router.get("", response_model=list[RunnerOut], dependencies=[Depends(get_current_user)])
def list_runners(db: Session = Depends(get_db)) -> list[RunnerOut]:
    """Monitoring state of every camera that was started at least once since the API started."""
    out = []
    for run in camera_runner.all():
        camera = db.get(Camera, run.camera_id)
        if camera is not None:
            out.append(_to_out(camera, run))
    return out


@router.get("/{camera_id}/runner", response_model=RunnerOut, dependencies=[Depends(get_current_user)])
def get_runner(camera_id: int, db: Session = Depends(get_db)) -> RunnerOut:
    camera = _get_camera_or_404(camera_id, db)
    return _to_out(camera, camera_runner.get(camera_id))


@router.post("/{camera_id}/runner", response_model=RunnerOut, dependencies=[admin_only])
def start_runner(
    camera_id: int,
    payload: RunnerStart,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    audit: Auditor = Depends(get_auditor),
) -> RunnerOut:
    """Start the selected analyses for this camera, reading its stream_source."""
    camera = _get_camera_or_404(camera_id, db)
    try:
        run = camera_runner.start(camera.id, camera.stream_source, list(payload.scripts))
    except RunnerError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    audit.log(actor, "monitoring.start", "camera", camera.id, commit=True, scripts=list(payload.scripts))
    background_tasks.add_task(manager.broadcast, _runner_message(camera.id, running=True))
    return _to_out(camera, run)


@router.delete("/{camera_id}/runner", response_model=RunnerOut, dependencies=[admin_only])
def stop_runner(
    camera_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    audit: Auditor = Depends(get_auditor),
) -> RunnerOut:
    """Stop this camera's analyses. Nobody is watching the camera any more, so
    its status becomes "unknown" (not "offline": the camera itself may be fine)."""
    camera = _get_camera_or_404(camera_id, db)
    run = camera_runner.stop(camera.id)
    audit.log(actor, "monitoring.stop", "camera", camera.id, commit=True)
    background_tasks.add_task(manager.broadcast, _runner_message(camera.id, running=False))
    if run is not None:
        status_message = _set_status(camera.id, CameraStatus.UNKNOWN)
        if status_message:
            background_tasks.add_task(manager.broadcast, status_message)
    db.refresh(camera)
    return _to_out(camera, run)
