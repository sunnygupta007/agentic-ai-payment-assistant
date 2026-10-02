from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Chat


async def save_message(db: AsyncSession, session_id: str, role: str, content: str, meta: str = "{}") -> Chat:
    chat = Chat(session_id=session_id, role=role, content=content, meta=meta)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_history(db: AsyncSession, session_id: str) -> list[Chat]:
    return (await db.execute(select(Chat).where(Chat.session_id == session_id).order_by(Chat.created_at.asc()))).scalars().all()
