from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..agents.orchestrator import handle_message
from ..db import SessionLocal
from ..security import enforce_rate_limit
from ..services.payment_service import get_demo_user
from .manager import manager

router = APIRouter()


@router.websocket("/ws/chat/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        async with SessionLocal() as db:
            user = await get_demo_user(db)
            await websocket.send_json({"type": "connected", "payload": {"session_id": session_id}})
            while True:
                payload = await websocket.receive_json()
                message = payload.get("message", "")
                enforce_rate_limit(session_id)
                await manager.send_json(session_id, {"type": "typing", "payload": {"active": True}})
                async for event in handle_message(db, session_id, user.id, message):
                    await manager.send_json(session_id, event)
                await manager.send_json(session_id, {"type": "typing", "payload": {"active": False}})
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
