import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jwt import PyJWTError
from starlette.concurrency import run_in_threadpool

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services.frame_store import frame_store
from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])

MAX_STREAM_SUBSCRIPTIONS = 64


def _is_active_user(username: str) -> bool:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        return user is not None and user.is_active


async def _authorize(websocket: WebSocket) -> bool:
    """Browsers can't set headers on a WebSocket handshake, so the JWT comes
    as a query param. Closes the socket (1008) and returns False if invalid."""
    token = websocket.query_params.get("token", "")
    try:
        username = decode_access_token(token).get("sub")
    except PyJWTError:
        username = None

    if not username or not await run_in_threadpool(_is_active_user, username):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    return True


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    if not await _authorize(websocket):
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # client sends nothing meaningful; just keeps the socket open
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket) -> None:
    """Live camera frames for the dashboard.

    Client -> server (text): {"subscribe": [camera_id, ...]} replaces the set
    of cameras this socket watches.
    Server -> client (binary): 4-byte big-endian camera_id, then the JPEG.

    One socket carries every camera, because browsers allow only ~6
    concurrent HTTP connections per host: one MJPEG <img> stream per camera
    would starve the dashboard's own API calls.
    """
    if not await _authorize(websocket):
        return
    await websocket.accept()

    subscribed: set[int] = set()
    sent_seq: dict[int, int] = {}
    wake = frame_store.subscribe()

    async def read_subscriptions() -> None:
        while True:
            try:
                message = json.loads(await websocket.receive_text())
            except json.JSONDecodeError:
                continue
            ids = message.get("subscribe") if isinstance(message, dict) else None
            if (
                isinstance(ids, list)
                and len(ids) <= MAX_STREAM_SUBSCRIPTIONS
                and all(isinstance(i, int) and not isinstance(i, bool) for i in ids)
            ):
                subscribed.clear()
                subscribed.update(ids)
                sent_seq.clear()
                wake.set()  # send current frames right away, not on the next publish

    async def send_frames() -> None:
        while True:
            await wake.wait()
            wake.clear()
            for camera_id in list(subscribed):
                frame = frame_store.latest(camera_id)
                if frame is not None and sent_seq.get(camera_id) != frame.seq:
                    # Mark first: a publish during this await must not be resent as a duplicate.
                    sent_seq[camera_id] = frame.seq
                    await websocket.send_bytes(camera_id.to_bytes(4, "big") + frame.jpeg)

    tasks = {asyncio.create_task(read_subscriptions()), asyncio.create_task(send_frames())}
    try:
        # Either side ending (client disconnect, send failure) ends the stream.
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect | RuntimeError):
                raise exc
    finally:
        for task in tasks:
            task.cancel()
        frame_store.unsubscribe(wake)
