from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jwt import PyJWTError

from app.core.security import decode_access_token
from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token", "")
    try:
        decode_access_token(token)
    except PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # client sends nothing meaningful; just keeps the socket open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
