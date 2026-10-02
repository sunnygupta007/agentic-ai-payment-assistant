from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import Transaction
from ..schemas import TransactionCreate
from ..services.analytics_service import serialize_txn
from ..services.payment_service import get_demo_user, simulate_transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/{session_id}")
async def list_transactions(session_id: str, db: AsyncSession = Depends(get_db)):
    txns = (await db.execute(select(Transaction).where(Transaction.session_id == session_id).order_by(Transaction.created_at.desc()))).scalars().all()
    return [serialize_txn(t) for t in txns]


@router.post("/simulate")
async def simulate(payload: TransactionCreate, db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    return await simulate_transaction(db, payload.session_id, user.id, payload.recipient, payload.amount, payload.category, payload.method)
