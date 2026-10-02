from collections import Counter
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..guardrails import check_prompt_injection
from ..security import sanitize_text
from ..services.audit_service import log_event
from ..services.invoice_service import create_invoice_payload
# from ..services.payment_service import create_recurring, top_up_wallet
from ..services.payment_service import (
    create_recurring,
    top_up_wallet,
    list_recurring_payments,
    recurring_payment_summary,
    pause_recurring_payment,
    resume_recurring_payment,
    delete_recurring_payment,
)
from ..utils import parse_amount, parse_recipient

from .budget_agent import budget_insights
from .fraud_agent import fraud_check
from .llm_client import stream_llm_or_fallback
from .memory import save_message
from .payment_agent import run_payment
from .router_agent import classify_intent
from .validation_agent import validate_payment_message
from ..models import Transaction
import re


async def get_latest_transaction(db: AsyncSession, session_id: str):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.session_id == session_id)
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def get_recent_transactions(db: AsyncSession, session_id: str, limit: int = 20):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.session_id == session_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def find_recurring_payment(
    db: AsyncSession,
    session_id: str,
    text: str,
):
    items = await list_recurring_payments(
        db,
        session_id,
    )

    lowered = text.lower()

    # First try ID lookup
    match = re.search(r"\b(\d+)\b", lowered)

    if match:

        target_id = int(match.group(1))

        for item in items:

            if item["id"] == target_id:
                return item

    # Then try recipient lookup

    for item in items:

        recipient = item["recipient"].lower()

        if recipient in lowered:
            return item

    return None

async def handle_message(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    message: str,
) -> AsyncGenerator[dict, None]:

    cleaned = sanitize_text(message)

    await save_message(db, session_id, "user", cleaned)

    guard = check_prompt_injection(cleaned)

    if not guard.allowed:
        await log_event(
            db,
            session_id,
            "prompt_injection_blocked",
            guard.reason,
            "critical",
        )

        text = (
            "I blocked that request because it appears to ask for "
            "hidden instructions or safety bypasses."
        )

        await save_message(db, session_id, "assistant", text)

        yield {"type": "final", "content": text}
        return

    intent = classify_intent(cleaned)

    yield {
        "type": "agent",
        "agent": "Router Agent",
        "status": f"Intent classified as {intent}",
    }

    # ==========================================================
    # WALLET TOP UP
    # ==========================================================

    if intent == "wallet_top_up":

        amount = parse_amount(cleaned)

        if not amount or amount <= 0:

            text = (
                "Please provide a valid amount."
                "Example: Add INR 5000 to wallet"
            )

            await save_message(db, session_id, "assistant", text)

            yield {"type": "final", "content": text}
            return

        result = await top_up_wallet(
            db,
            session_id,
            user_id,
            amount,
            "ai_command",
        )

        yield {"type": "wallet", "payload": result}

        text = f"""
💰 Wallet Top-Up Successful

Amount Added: ₹{amount:,.0f}

Current Balance: ₹{result['balance']:,.0f}

Status: Completed
"""

        await save_message(db, session_id, "assistant", text)

        yield {"type": "final", "content": text}

        return

    # ==========================================================
    # PAYMENT FLOW
    # ==========================================================

    if intent == "payment":

        validation = validate_payment_message(cleaned)

        yield {
            "type": "tool",
            "tool": "validate_transaction_data",
            "status": "completed",
            "payload": validation,
        }

        if not validation["valid"]:

            text = (
                f"I need the following information: "
                f"{', '.join(validation['missing'])}"
            )

            await save_message(db, session_id, "assistant", text)

            yield {"type": "final", "content": text}

            return

        risk = await fraud_check(
            validation["amount"],
            validation["recipient"],
        )

        yield {
            "type": "tool",
            "tool": "detect_fraud_risk",
            "status": "completed",
            "payload": risk,
        }

        result = await run_payment(
            db,
            session_id,
            user_id,
            validation["recipient"],
            validation["amount"],
        )

        yield {
            "type": "transaction",
            "payload": result,
        }

        if result["status"] == "approval_required":

            text = f"""
🚨 Human Approval Required

Recipient: {validation['recipient']}
Amount: ₹{validation['amount']:,.0f}

Risk Level: {result['risk_level']}

Reason:
{result['reason']}

Status: Waiting For Approval
"""

            yield {
                "type": "approval",
                "payload": result,
            }

        elif result["status"] == "completed":

            text = f"""
🧾 Payment Request Processed

Recipient: {validation['recipient']}
Amount: ₹{validation['amount']:,.0f}

✅ Validation Passed
✅ Fraud Check Completed

💸 Simulated Payment Successful

Transaction ID: {result['transaction_id']}
Risk Level: {result['risk_level']}

Status: Completed
"""

        else:

            text = f"""
❌ Payment Failed

Reason:
{result['reason']}
"""

        await save_message(db, session_id, "assistant", text)

        yield {"type": "final", "content": text}

        return

    # ==========================================================
    # ANALYTICS
    # ==========================================================

    if intent == "analytics":

        data = await budget_insights(
            db,
            session_id,
        )

        yield {
            "type": "analytics",
            "payload": data,
        }

        text = (
            f"Your simulated spend is INR "
            f"{data['total_spend']:,.0f} across "
            f"{data['transaction_count']} transactions."
        )

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {"type": "final", "content": text}

        return

    # ==========================================================
    # MONTHLY SPENDING
    # ==========================================================

    if intent == "monthly_spending":

        data = await budget_insights(
            db,
            session_id,
        )

        text = f"""
    📅 Monthly Spending

    Total Spend:
    ₹{data.get('monthly_spend', 0):,.0f}

    Top Category:
    {data.get('top_category', 'N/A')}

    Top Recipient:
    {data.get('top_recipient', 'N/A')}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # WEEKLY SPENDING
    # ==========================================================

    if intent == "weekly_spending":

        data = await budget_insights(
            db,
            session_id,
        )

        text = f"""
    📊 Weekly Spending

    Total Spend:
    ₹{data.get('weekly_spend', 0):,.0f}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # DAILY SPENDING
    # ==========================================================

    if intent == "daily_spending":

        data = await budget_insights(
            db,
            session_id,
        )

        text = f"""
    📈 Daily Spending

    Total Spend:
    ₹{data.get('daily_spend', 0):,.0f}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # TOP CATEGORY
    # ==========================================================

    if intent == "top_category":

        data = await budget_insights(
            db,
            session_id,
        )

        text = f"""
    🏆 Highest Spending Category

    {data.get('top_category', 'N/A')}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # TOP RECIPIENT
    # ==========================================================

    if intent == "top_recipient":

        data = await budget_insights(
            db,
            session_id,
        )

        text = f"""
    👤 Most Frequent Recipient

    {data.get('top_recipient', 'N/A')}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return

    # ==========================================================
    # TRANSACTION QUERY
    # ==========================================================

    if intent == "transaction_query":
        txns = await get_recent_transactions(db, session_id, limit=20)

        if not txns:
            text = "No transactions found yet in this demo session."
            await save_message(db, session_id, "assistant", text)
            yield {"type": "final", "content": text}
            return

        recipient_counts = Counter(
            (txn.recipient or "Unknown").strip().lower() for txn in txns
        )
        top_recipient, top_recipient_count = recipient_counts.most_common(1)[0]

        latest = txns[0]

        category_totals = {}
        for txn in txns:
            category = txn.category or "Transfer"
            category_totals[category] = category_totals.get(category, 0) + float(txn.amount or 0)

        top_category = max(category_totals, key=category_totals.get)

        text = f"""
📊 Transaction Insights

Most frequent recipient: {top_recipient.title()} ({top_recipient_count} payments)
Latest transaction: {latest.recipient} · ₹{latest.amount:,.0f} · {latest.transaction_id}
Highest spend category: {top_category} · ₹{category_totals[top_category]:,.0f}

If you want, I can also generate an invoice from the latest transaction or show spending advice.
"""

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    # ==========================================================
    # RECURRING PAYMENTS
    # ==========================================================

    if intent == "recurring":

        amount = parse_amount(cleaned) or 500

        recipient = parse_recipient(cleaned)

        frequency = (
            "weekly"
            if "weekly" in cleaned.lower()
            else "monthly"
        )

        recurring = await create_recurring(
            db,
            session_id,
            user_id,
            recipient,
            amount,
            frequency,
        )

        text = f"""
🔁 Recurring Payment Created

Recipient: {recipient}
Amount: ₹{amount:,.0f}

Frequency: {frequency}

Recurring ID: {recurring.id}

Status: Active
"""

        yield {
            "type": "recurring",
            "payload": {
                "id": recurring.id,
                "recipient": recipient,
                "amount": amount,
                "frequency": frequency,
            },
        }

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {"type": "final", "content": text}

        return

    # ==========================================================
    # LIST RECURRING PAYMENTS
    # ==========================================================

    if intent == "list_recurring":

        items = await list_recurring_payments(
            db,
            session_id,
        )

        if not items:

            text = "No recurring payments found."

            await save_message(
                db,
                session_id,
                "assistant",
                text,
            )

            yield {
                "type": "final",
                "content": text,
            }

            return

        lines = ["🔁 Recurring Payments\n"]

        for item in items:

            status = (
                "Active"
                if item["active"]
                else "Paused"
            )

            lines.append(
                f"ID: {item['id']} | "
                f"{item['recipient']} | "
                f"₹{item['amount']:,.0f} | "
                f"{item['frequency']} | "
                f"{status}"
            )

        text = "\n".join(lines)

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return

    if intent == "pause_recurring":

        item = await find_recurring_payment(
    db,
    session_id,
    cleaned,
)

        if not item:
            text = "No matching recurring payment found."
            await save_message(db, session_id, "assistant", text)
            yield {"type": "final", "content": text}
            return

        result = await pause_recurring_payment(
            db,
            item["id"],
            session_id,
        )

        text = (
            f"⏸️ Recurring payment paused\n\n"
            f"Recipient: {item['recipient']}\n"
            f"Amount: ₹{item['amount']:,.0f}"
        )

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    if intent == "resume_recurring":

        item = await find_recurring_payment(
            db,
            session_id,
            cleaned,
        )

        if not item:
            text = "No matching recurring payment found."
            await save_message(db, session_id, "assistant", text)
            yield {"type": "final", "content": text}
            return

        await resume_recurring_payment(
            db,
            item["id"],
            session_id,
        )

        text = (
            f"▶️ Recurring payment resumed\n\n"
            f"Recipient: {item['recipient']}\n"
            f"Amount: ₹{item['amount']:,.0f}"
        )

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    if intent == "delete_recurring":

        item = await find_recurring_payment(
            db,
            session_id,
            cleaned,
        )

        if not item:
            text = "No matching recurring payment found."
            await save_message(db, session_id, "assistant", text)
            yield {"type": "final", "content": text}
            return

        await delete_recurring_payment(
            db,
            item["id"],
            session_id,
        )

        text = (
            f"🗑️ Recurring payment deleted\n\n"
            f"Recipient: {item['recipient']}\n"
            f"Amount: ₹{item['amount']:,.0f}"
        )

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    # ==========================================================
    # RECURRING ANALYSIS
    # ==========================================================

    if intent == "recurring_analysis":

        summary = await recurring_payment_summary(
            db,
            session_id,
        )

        text = f"""
    📊 Recurring Payment Analysis

    Active Payments:
    {summary["active_count"]}

    Monthly Commitment:
    ₹{summary["monthly_commitment"]:,.0f}

    Annual Projection:
    ₹{summary["annual_projection"]:,.0f}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # RECURRING PROJECTION
    # ==========================================================

    if intent == "recurring_projection":

        summary = await recurring_payment_summary(
            db,
            session_id,
        )

        text = f"""
    📈 Subscription Cost Projection

    Monthly Spend:
    ₹{summary["monthly_commitment"]:,.0f}

    Projected Annual Cost:
    ₹{summary["annual_projection"]:,.0f}
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return


    # ==========================================================
    # RECURRING OPTIMIZATION
    # ==========================================================

    if intent == "recurring_optimization":

        summary = await recurring_payment_summary(
            db,
            session_id,
        )

        text = f"""
    💡 Subscription Optimization

    Active Payments:
    {summary["active_count"]}

    Monthly Commitment:
    ₹{summary["monthly_commitment"]:,.0f}

    Suggestions:

    • Review unused subscriptions
    • Audit recurring payments monthly
    • Pause low-value subscriptions
    • Consolidate overlapping services
    """

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {
            "type": "final",
            "content": text,
        }

        return

    # ==========================================================
    # FINANCIAL ADVICE
    # ==========================================================

    if intent == "financial_advice":
        data = await budget_insights(db, session_id)

        prompt = f"""
You are a financial advisor for a simulated fintech demo.

User asked:
{cleaned}

Spending summary:

Total spend:
INR {data.get('total_spend', 0):,.0f}

Daily spend:
INR {data.get('daily_spend', 0):,.0f}

Weekly spend:
INR {data.get('weekly_spend', 0):,.0f}

Monthly spend:
INR {data.get('monthly_spend', 0):,.0f}

Transaction count:
{data.get('transaction_count', 0)}

Top recipient:
{data.get('top_recipient', 'N/A')}

Top category:
{data.get('top_category', 'N/A')}

Category breakdown:
{data.get('category_breakdown', [])}

Expense trend:
{data.get('expense_trend', [])}

Fraud insights:
{data.get('fraud_insights', [])}

Give:
1. Short summary
2. 3 practical ways to improve spending
3. Mention the highest spending category
4. Mention the most frequent recipient
5. Keep the answer concise and actionable
"""

        fallback = (
            f"Your simulated spend is INR {data.get('total_spend', 0):,.0f} "
            f"across {data.get('transaction_count', 0)} transactions. "
            "Try reducing discretionary spend, reviewing recurring payments, "
            "and setting a weekly budget."
        )

        chunks = []
        async for token in stream_llm_or_fallback(prompt, fallback):
            chunks.append(token)
            yield {"type": "token", "content": token}

        text = "".join(chunks).strip() or fallback

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    # ==========================================================
    # INVOICE FROM TRANSACTION
    # ==========================================================

    if intent == "invoice_from_transaction":
        latest_txn = await get_latest_transaction(db, session_id)

        if not latest_txn:
            text = "No recent transaction found to generate an invoice from."
            await save_message(db, session_id, "assistant", text)
            yield {"type": "final", "content": text}
            return

        payload = create_invoice_payload(
            latest_txn.recipient,
            latest_txn.amount,
            f"Generated from transaction {latest_txn.transaction_id}",
        )

        await log_event(
            db,
            session_id,
            "invoice_created",
            f"Generated invoice {payload['invoice_id']} from latest transaction {latest_txn.transaction_id}.",
        )

        text = f"""
📄 Invoice Generated From Latest Transaction

Invoice ID: {payload['invoice_id']}
Client: {latest_txn.recipient}
Amount: ₹{latest_txn.amount:,.0f}
Source Transaction: {latest_txn.transaction_id}
Status: Draft
"""

        yield {"type": "invoice", "payload": payload}
        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    # ==========================================================
    # INVOICE
    # ==========================================================

    if intent == "invoice":

        amount = parse_amount(cleaned) or 3500

        client = parse_recipient(cleaned)

        payload = create_invoice_payload(
            client,
            amount,
            "Demo invoice generated by AI assistant",
        )

        await log_event(
            db,
            session_id,
            "invoice_created",
            f"Generated invoice {payload['invoice_id']}.",
        )

        text = f"""
📄 Invoice Generated

Invoice ID: {payload['invoice_id']}

Client: {client}

Amount: ₹{amount:,.0f}

Status: Draft
"""

        yield {
            "type": "invoice",
            "payload": payload,
        }

        await save_message(
            db,
            session_id,
            "assistant",
            text,
        )

        yield {"type": "final", "content": text}

        return

    # ==========================================================
    # GENERAL CHAT / UNKNOWN
    # ==========================================================

    if intent in {"general", "unknown"}:
        text = (
            "🤖 Agentic AI Payment Assistant\n\n"
            "I can help with:\n"
            "• Simulated Payments\n"
            "• Wallet Management\n"
            "• Invoice Generation\n"
            "• Recurring Payments\n"
            "• Fraud Detection\n"
            "• Spending Insights\n\n"
            "Try:\n"
            "• Pay INR 500 to Rahul\n"
            "• Add INR 2000 to wallet\n"
            "• Generate invoice from latest transaction\n"
            "• How can I improve my spending?"
        )

        await save_message(db, session_id, "assistant", text)
        yield {"type": "final", "content": text}
        return

    text = (
        "I can help with simulated payments, invoices, wallet top-ups, "
        "recurring transfers, fraud analysis, and spending insights."
    )

    await save_message(db, session_id, "assistant", text)
    yield {"type": "final", "content": text}