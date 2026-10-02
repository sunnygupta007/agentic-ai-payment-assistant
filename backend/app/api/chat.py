from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..agents.memory import get_history
from ..agents.orchestrator import handle_message
from ..db import get_db
from ..schemas import ChatRequest
from ..security import enforce_rate_limit
from ..services.payment_service import get_demo_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/history/{session_id}")
async def history(session_id: str, db: AsyncSession = Depends(get_db)):
    messages = await get_history(db, session_id)
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]


@router.post("/send")
async def send_chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    enforce_rate_limit(payload.session_id)
    user = await get_demo_user(db)
    final = ""
    events = []
    async for event in handle_message(db, payload.session_id, user.id, payload.message):
        events.append(event)
        if event["type"] == "final":
            final = event["content"]
    return {"message": final, "events": events}
