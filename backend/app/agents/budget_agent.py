from sqlalchemy.ext.asyncio import AsyncSession
from ..services.analytics_service import spending_summary


async def budget_insights(db: AsyncSession, session_id: str) -> dict:
    return await spending_summary(db, session_id)
