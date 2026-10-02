from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import ApprovalDecision
from ..services.payment_service import decide_approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("/{approval_id}/decision")
async def approval_decision(approval_id: int, payload: ApprovalDecision, db: AsyncSession = Depends(get_db)):
    return await decide_approval(db, approval_id, payload.decision)
