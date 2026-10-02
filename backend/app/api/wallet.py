from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import WalletTopUp
from ..services.payment_service import get_demo_user, top_up_wallet

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.post("/top-up")
async def top_up(payload: WalletTopUp, db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    return await top_up_wallet(db, payload.session_id, user.id, payload.amount, payload.source)
