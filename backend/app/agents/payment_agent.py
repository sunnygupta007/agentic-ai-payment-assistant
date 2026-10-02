from sqlalchemy.ext.asyncio import AsyncSession
from ..services.payment_service import simulate_transaction


async def run_payment(db: AsyncSession, session_id: str, user_id: int, recipient: str, amount: float, category: str = "Transfer") -> dict:
    return await simulate_transaction(db, session_id, user_id, recipient, amount, category=category)
