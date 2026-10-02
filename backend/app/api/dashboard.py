from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..services.analytics_service import dashboard_payload
from ..services.payment_service import get_demo_user

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/{session_id}")
async def dashboard(session_id: str, db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    return await dashboard_payload(db, session_id, user.id)


@router.get("/api/insights/{session_id}")
async def insights(session_id: str, db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    data = await dashboard_payload(db, session_id, user.id)
    return {"recommendations": data["analytics"]["recommendations"], "fraud_insights": data["analytics"]["fraud_insights"]}
