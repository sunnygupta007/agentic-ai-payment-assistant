from ..websocket.manager import manager


async def notify_session(session_id: str, event: str, payload: dict) -> None:
    await manager.send_json(session_id, {"type": event, "payload": payload})
