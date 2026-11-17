from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jwt import PyJWTError
from starlette.concurrency import run_in_threadpool

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])


def _is_active_user(username: str) -> bool:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        return user is not None and user.is_active


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    # Browsers can't set headers on a WebSocket handshake, so the JWT comes as a query param.
    token = websocket.query_params.get("token", "")
    try:
        username = decode_access_token(token).get("sub")
    except PyJWTError:
        username = None

    if not username or not await run_in_threadpool(_is_active_user, username):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # client sends nothing meaningful; just keeps the socket open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
