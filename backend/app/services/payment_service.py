from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..guardrails import transaction_needs_approval
from ..models import Approval, RecurringPayment, Transaction, User, Wallet
from ..utils import new_transaction_id
from .audit_service import log_event


async def get_demo_user(db: AsyncSession) -> User:
    user = (
        await db.execute(
            select(User).where(User.email == "demo@agenticpay.ai")
        )
    ).scalar_one_or_none()
    if user:
        return user

    user = User(name="Demo Founder", email="demo@agenticpay.ai")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(Wallet(user_id=user.id, balance=25000, currency="INR"))
    await db.commit()
    return user


async def get_wallet(db: AsyncSession, user_id: int) -> Wallet:
    wallet = (
        await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    ).scalar_one()
    return wallet


async def top_up_wallet(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    amount: float,
    source: str = "ui",
) -> dict:
    wallet = await get_wallet(db, user_id)
    wallet.balance += amount
    await db.commit()
    await db.refresh(wallet)

    await log_event(
        db,
        session_id,
        "wallet_top_up",
        f"Added simulated wallet funds: INR {amount:,.0f} via {source}.",
    )
    return {
        "status": "completed",
        "amount": amount,
        "balance": wallet.balance,
        "currency": wallet.currency,
        "source": source,
    }


async def assess_risk(amount: float, recipient: str) -> tuple[float, str]:
    score = 0.12
    if amount >= 10000:
        score += 0.52
    if "unknown" in recipient.lower() or "account" in recipient.lower():
        score += 0.32
    if amount % 999 == 0:
        score += 0.1
    level = "high" if score >= 0.7 else "medium" if score >= 0.45 else "low"
    return min(score, 0.98), level


async def simulate_transaction(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    recipient: str,
    amount: float,
    category: str = "Transfer",
    method: str = "UPI",
) -> dict:
    score, risk = await assess_risk(amount, recipient)
    needs_approval, reason = transaction_needs_approval(amount, recipient, score)
    txn_id = new_transaction_id()

    if needs_approval:
        approval = Approval(
            session_id=session_id,
            transaction_id=txn_id,
            amount=amount,
            recipient=recipient,
            reason=reason,
        )
        transaction = Transaction(
            transaction_id=txn_id,
            session_id=session_id,
            user_id=user_id,
            recipient=recipient,
            amount=amount,
            category=category,
            method=method,
            status="approval_required",
            risk_level=risk,
        )
        db.add_all([approval, transaction])
        await db.commit()
        await db.refresh(approval)

        await log_event(db, session_id, "approval_requested", reason, "warning")
        return {
            "status": "approval_required",
            "approval_id": approval.id,
            "transaction_id": txn_id,
            "risk_level": risk,
            "reason": reason,
            "amount": amount,
            "recipient": recipient,
        }

    wallet = await get_wallet(db, user_id)
    if wallet.balance < amount:
        await log_event(
            db,
            session_id,
            "transaction_rejected",
            "Insufficient demo wallet balance.",
            "warning",
        )
        return {
            "status": "rejected",
            "reason": "Insufficient demo wallet balance.",
            "risk_level": risk,
        }

    wallet.balance -= amount
    transaction = Transaction(
        transaction_id=txn_id,
        session_id=session_id,
        user_id=user_id,
        recipient=recipient,
        amount=amount,
        category=category,
        method=method,
        status="completed",
        risk_level=risk,
    )
    db.add(transaction)
    await db.commit()

    await log_event(
        db,
        session_id,
        "transaction_completed",
        f"Simulated {method} payment of INR {amount:,.0f} to {recipient}.",
    )
    return {
        "status": "completed",
        "transaction_id": txn_id,
        "risk_level": risk,
        "amount": amount,
        "recipient": recipient,
    }


async def decide_approval(db: AsyncSession, approval_id: int, decision: str) -> dict:
    approval = await db.get(Approval, approval_id)
    if not approval or approval.status != "pending":
        return {"status": "not_found"}

    approval.status = decision
    approval.decided_at = datetime.utcnow()

    transaction = (
        await db.execute(
            select(Transaction).where(
                Transaction.transaction_id == approval.transaction_id
            )
        )
    ).scalar_one_or_none()

    if decision == "approved" and transaction:
        wallet = await get_wallet(db, transaction.user_id)
        if wallet.balance >= transaction.amount:
            wallet.balance -= transaction.amount
            transaction.status = "completed"
            await log_event(
                db,
                approval.session_id,
                "approval_approved",
                f"Approved and simulated payment to {approval.recipient}.",
            )
        else:
            transaction.status = "rejected"
            approval.status = "rejected"
            await log_event(
                db,
                approval.session_id,
                "approval_rejected",
                "Approval failed due to insufficient demo balance.",
                "warning",
            )
    elif transaction:
        transaction.status = "rejected"
        await log_event(
            db,
            approval.session_id,
            "approval_rejected",
            f"Rejected payment to {approval.recipient}.",
            "warning",
        )

    await db.commit()
    return {"status": approval.status, "transaction_id": approval.transaction_id}


def _frequency_to_timedelta(frequency: str) -> timedelta:
    value = (frequency or "monthly").lower()
    if value == "weekly":
        return timedelta(days=7)
    if value == "daily":
        return timedelta(days=1)
    if value == "yearly":
        return timedelta(days=365)
    return timedelta(days=30)


async def create_recurring(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    recipient: str,
    amount: float,
    frequency: str,
) -> RecurringPayment:
    next_run = datetime.utcnow() + _frequency_to_timedelta(frequency)
    recurring = RecurringPayment(
        session_id=session_id,
        user_id=user_id,
        recipient=recipient,
        amount=amount,
        frequency=frequency,
        next_run_at=next_run,
        active=True,
    )
    db.add(recurring)
    await db.commit()
    await db.refresh(recurring)

    await log_event(
        db,
        session_id,
        "recurring_created",
        f"Created {frequency} simulated payment to {recipient}.",
    )
    return recurring


def serialize_recurring(recurring: RecurringPayment) -> dict[str, Any]:
    return {
        "id": recurring.id,
        "session_id": recurring.session_id,
        "user_id": recurring.user_id,
        "recipient": recurring.recipient,
        "amount": recurring.amount,
        "frequency": recurring.frequency,
        "active": recurring.active,
        "next_run_at": recurring.next_run_at.isoformat()
        if recurring.next_run_at
        else None,
        "created_at": recurring.created_at.isoformat()
        if recurring.created_at
        else None,
    }


async def get_recurring_payment(
    db: AsyncSession,
    recurring_id: int,
    session_id: str | None = None,
) -> RecurringPayment | None:
    stmt = select(RecurringPayment).where(RecurringPayment.id == recurring_id)
    if session_id:
        stmt = stmt.where(RecurringPayment.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_recurring_payments(
    db: AsyncSession,
    session_id: str,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    stmt = (
        select(RecurringPayment)
        .where(RecurringPayment.session_id == session_id)
        .order_by(RecurringPayment.created_at.desc())
    )
    if active_only:
        stmt = stmt.where(RecurringPayment.active.is_(True))

    result = await db.execute(stmt)
    items = result.scalars().all()
    return [serialize_recurring(item) for item in items]


async def pause_recurring_payment(
    db: AsyncSession,
    recurring_id: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    recurring = await get_recurring_payment(db, recurring_id, session_id)
    if not recurring:
        return {"status": "not_found"}

    recurring.active = False
    await db.commit()

    await log_event(
        db,
        recurring.session_id,
        "recurring_paused",
        f"Paused recurring payment to {recurring.recipient}.",
    )
    return {"status": "paused", "recurring": serialize_recurring(recurring)}


async def resume_recurring_payment(
    db: AsyncSession,
    recurring_id: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    recurring = await get_recurring_payment(db, recurring_id, session_id)
    if not recurring:
        return {"status": "not_found"}

    recurring.active = True
    if not recurring.next_run_at:
        recurring.next_run_at = datetime.utcnow() + _frequency_to_timedelta(
            recurring.frequency
        )
    await db.commit()

    await log_event(
        db,
        recurring.session_id,
        "recurring_resumed",
        f"Resumed recurring payment to {recurring.recipient}.",
    )
    return {"status": "resumed", "recurring": serialize_recurring(recurring)}


async def delete_recurring_payment(
    db: AsyncSession,
    recurring_id: int,
    session_id: str | None = None,
) -> dict[str, Any]:
    recurring = await get_recurring_payment(db, recurring_id, session_id)
    if not recurring:
        return {"status": "not_found"}

    payload = serialize_recurring(recurring)
    await db.delete(recurring)
    await db.commit()

    await log_event(
        db,
        payload["session_id"],
        "recurring_deleted",
        f"Deleted recurring payment to {payload['recipient']}.",
    )
    return {"status": "deleted", "recurring": payload}


async def recurring_payment_summary(
    db: AsyncSession,
    session_id: str,
) -> dict[str, Any]:
    result = await db.execute(
        select(RecurringPayment)
        .where(RecurringPayment.session_id == session_id)
        .order_by(RecurringPayment.created_at.desc())
    )
    items = result.scalars().all()

    def monthly_equivalent(item: RecurringPayment) -> float:
        freq = (item.frequency or "monthly").lower()
        if freq == "weekly":
            return float(item.amount) * 4.33
        if freq == "daily":
            return float(item.amount) * 30
        if freq == "yearly":
            return float(item.amount) / 12
        return float(item.amount)

    active_items = [item for item in items if item.active]
    monthly_commitment = sum(monthly_equivalent(item) for item in active_items)
    annual_projection = monthly_commitment * 12

    recipient_totals: dict[str, float] = defaultdict(float)
    for item in active_items:
        recipient_totals[item.recipient] += monthly_equivalent(item)

    biggest = max(active_items, key=monthly_equivalent) if active_items else None

    return {
        "total_recurring": len(items),
        "active_count": len(active_items),
        "inactive_count": len(items) - len(active_items),
        "monthly_commitment": round(monthly_commitment, 2),
        "annual_projection": round(annual_projection, 2),
        "largest_recurring": serialize_recurring(biggest) if biggest else None,
        "by_recipient": [
            {"recipient": recipient, "monthly_amount": round(amount, 2)}
            for recipient, amount in sorted(
                recipient_totals.items(), key=lambda x: x[1], reverse=True
            )
        ],
        "items": [serialize_recurring(item) for item in items],
    }