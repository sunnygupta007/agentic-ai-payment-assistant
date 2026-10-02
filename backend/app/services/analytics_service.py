from datetime import datetime, timedelta
from collections import Counter
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import AuditLog, Approval, Transaction, Wallet


async def spending_summary(db: AsyncSession, session_id: str) -> dict:
    txns = (await db.execute(select(Transaction).where(Transaction.session_id == session_id).order_by(Transaction.created_at.desc()))).scalars().all()
    completed = [t for t in txns if t.status == "completed"]
    now = datetime.utcnow()

    daily_spend = 0
    weekly_spend = 0
    monthly_spend = 0

    recipient_totals: dict[str, float] = defaultdict(float)
    recipient_counts = Counter()
    by_category: dict[str, float] = defaultdict(float)
    trend: dict[str, float] = defaultdict(float)

    for txn in completed:

        by_category[txn.category] += txn.amount
        trend[txn.created_at.strftime("%b %d")] += txn.amount

        age = now - txn.created_at

        if age.days == 0:
            daily_spend += txn.amount

        if age.days <= 7:
            weekly_spend += txn.amount

        if age.days <= 30:
            monthly_spend += txn.amount

        recipient_totals[txn.recipient] += txn.amount
        recipient_counts[txn.recipient] += 1

    high_risk = [t for t in txns if t.risk_level in {"medium", "high"}]
    top_recipient = None

    if recipient_counts:
        top_recipient = recipient_counts.most_common(1)[0][0]

    top_category = None

    if by_category:
        top_category = max(
            by_category,
            key=by_category.get,
        )

    return {
                "daily_spend": daily_spend,
        "weekly_spend": weekly_spend,
        "monthly_spend": monthly_spend,

        "top_recipient": top_recipient,
        "top_category": top_category,

        "recipient_breakdown": [
            {
                "recipient": recipient,
                "amount": amount,
            }
            for recipient, amount in recipient_totals.items()
        ],

        "total_spend": sum(t.amount for t in completed),
        "transaction_count": len(txns),
        "category_breakdown": [{"label": k, "value": v} for k, v in by_category.items()],
        "expense_trend": [{"label": k, "value": v} for k, v in trend.items()],
        "fraud_insights": [{"transaction_id": t.transaction_id, "recipient": t.recipient, "risk_level": t.risk_level} for t in high_risk[:5]],
        "recommendations": [
            "Keep large transfers behind approvals for better control.",
            "Recurring payments are healthy when reviewed weekly.",
            "Food and subscription spend can be grouped for clearer forecasting.",
        ],
    }


async def dashboard_payload(db: AsyncSession, session_id: str, user_id: int) -> dict:
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one()
    txns = (await db.execute(select(Transaction).where(Transaction.session_id == session_id).order_by(Transaction.created_at.desc()).limit(8))).scalars().all()
    approvals = (await db.execute(select(Approval).where(Approval.session_id == session_id, Approval.status == "pending").order_by(Approval.created_at.desc()))).scalars().all()
    logs = (await db.execute(select(AuditLog).where(AuditLog.session_id == session_id).order_by(AuditLog.created_at.desc()).limit(8))).scalars().all()
    analytics = await spending_summary(db, session_id)
    return {
        "wallet": {"balance": wallet.balance, "currency": wallet.currency},
        "transactions": [serialize_txn(t) for t in txns],
        "approvals": [serialize_approval(a) for a in approvals],
        "logs": [{"type": l.event_type, "message": l.message, "severity": l.severity, "created_at": l.created_at.isoformat()} for l in logs],
        "analytics": analytics,
    }


def serialize_txn(t: Transaction) -> dict:
    return {
        "id": t.id,
        "transaction_id": t.transaction_id,
        "recipient": t.recipient,
        "amount": t.amount,
        "category": t.category,
        "method": t.method,
        "status": t.status,
        "risk_level": t.risk_level,
        "created_at": t.created_at.isoformat(),
    }


def serialize_approval(a: Approval) -> dict:
    return {
        "id": a.id,
        "transaction_id": a.transaction_id,
        "amount": a.amount,
        "recipient": a.recipient,
        "reason": a.reason,
        "status": a.status,
        "created_at": a.created_at.isoformat(),
    }
