from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Approval, RecurringPayment, Session, Transaction, User, Wallet
from .services.audit_service import log_event
from .services.payment_service import get_demo_user


async def seed_demo(db: AsyncSession) -> str:
    user = await get_demo_user(db)
    session = (await db.execute(select(Session).where(Session.id == "demo-session"))).scalar_one_or_none()
    if not session:
        session = Session(id="demo-session", user_id=user.id, title="Hackathon demo")
        db.add(session)
        await db.commit()

    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
    wallet.balance = 25000
    existing = (await db.execute(select(Transaction).where(Transaction.session_id == session.id))).scalars().first()
    if not existing:
        db.add_all([
            Transaction(transaction_id="TXN-DEMO-FOOD", session_id=session.id, user_id=user.id, recipient="Urban Cafe", amount=850, category="Food", method="UPI", status="completed", risk_level="low", created_at=datetime.utcnow() - timedelta(days=5)),
            Transaction(transaction_id="TXN-DEMO-SAAS", session_id=session.id, user_id=user.id, recipient="Design Cloud", amount=2200, category="Subscriptions", method="Wallet", status="completed", risk_level="low", created_at=datetime.utcnow() - timedelta(days=3)),
            Transaction(transaction_id="TXN-DEMO-TRAVEL", session_id=session.id, user_id=user.id, recipient="Metro Card", amount=1200, category="Travel", method="UPI", status="completed", risk_level="low", created_at=datetime.utcnow() - timedelta(days=2)),
            Transaction(transaction_id="TXN-DEMO-RISK", session_id=session.id, user_id=user.id, recipient="Unknown account", amount=18000, category="Transfer", method="Bank", status="approval_required", risk_level="high"),
            Approval(session_id=session.id, transaction_id="TXN-DEMO-RISK", amount=18000, recipient="Unknown account", reason="Unknown recipient and large amount requires approval."),
            RecurringPayment(session_id=session.id, user_id=user.id, recipient="Workspace Tools", amount=999, frequency="monthly", next_run_at=datetime.utcnow() + timedelta(days=8)),
        ])
        await db.commit()
        await log_event(db, session.id, "fraud_alert", "High-risk pending transfer seeded for demo.", "warning")
    return session.id
