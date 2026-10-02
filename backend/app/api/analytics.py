from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import InvoiceCreate, RecurringCreate
from ..services.analytics_service import spending_summary
from ..services.audit_service import log_event
from ..services.invoice_service import create_invoice_payload
from ..services.payment_service import create_recurring, get_demo_user

router = APIRouter(tags=["analytics"])


@router.get("/api/analytics/spending/{session_id}")
async def spending(session_id: str, db: AsyncSession = Depends(get_db)):
    return await spending_summary(db, session_id)


@router.post("/api/recurring/create")
async def recurring(payload: RecurringCreate, db: AsyncSession = Depends(get_db)):
    user = await get_demo_user(db)
    item = await create_recurring(db, payload.session_id, user.id, payload.recipient, payload.amount, payload.frequency)
    return {"id": item.id, "status": "created"}


@router.post("/api/invoice/create")
async def invoice(payload: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    data = create_invoice_payload(payload.client, payload.amount, payload.description)
    await log_event(db, payload.session_id, "invoice_created", f"Generated invoice {data['invoice_id']}.")
    return data
