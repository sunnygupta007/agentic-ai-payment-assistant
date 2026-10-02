from sqlalchemy.ext.asyncio import AsyncSession
from ..models import AuditLog


async def log_event(db: AsyncSession, session_id: str, event_type: str, message: str, severity: str = "info") -> AuditLog:
    event = AuditLog(session_id=session_id, event_type=event_type, message=message, severity=severity)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
