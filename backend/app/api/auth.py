from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import Session
from ..schemas import SessionCreateResponse
from ..services.payment_service import get_demo_user
from ..utils import new_session_id

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    session = Session(id=new_session_id(), user_id=user.id)
    db.add(session)
    await db.commit()
    return SessionCreateResponse(session_id=session.id, user_id=user.id)
