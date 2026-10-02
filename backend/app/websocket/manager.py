from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        self.active.get(session_id, set()).discard(websocket)

    async def send_json(self, session_id: str, data: dict) -> None:
        for socket in list(self.active.get(session_id, set())):
            await socket.send_json(data)


manager = ConnectionManager()
