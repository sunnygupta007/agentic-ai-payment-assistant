def classify_intent(message: str) -> str:
    text = " ".join(message.lower().split())

    def has_any(words):
        return any(word in text for word in words)

    # ==========================================================
    # WALLET
    # ==========================================================

    if (
        has_any([
            "top up",
            "top-up",
            "add money",
            "recharge wallet",
            "load wallet",
        ])
        or ("add" in text and "wallet" in text)
    ):
        return "wallet_top_up"

    # ==========================================================
    # RECURRING PAYMENT MANAGEMENT
    # ==========================================================

    if (
        has_any(["show", "list", "view", "display"])
        and has_any(["recurring", "subscription"])
    ):
        return "list_recurring"

    if (
        has_any(["pause", "stop", "disable", "suspend"])
        and has_any(["recurring", "subscription", "payment"])
    ):
        return "pause_recurring"

    if (
        has_any(["resume", "restart", "enable"])
        and has_any(["recurring", "subscription", "payment"])
    ):
        return "resume_recurring"

    if (
        has_any(["delete", "remove", "cancel"])
        and has_any(["recurring", "subscription", "payment"])
    ):
        return "delete_recurring"

    if (
        has_any(["analyze", "review", "inspect"])
        and has_any(["recurring", "subscription"])
    ):
        return "recurring_analysis"

    if (
        has_any(["annual", "yearly", "projection"])
        and has_any(["recurring", "subscription"])
    ):
        return "recurring_projection"

    if (
        has_any(["optimize", "reduce", "save"])
        and has_any(["recurring", "subscription"])
    ):
        return "recurring_optimization"

    # ==========================================================
    # INVOICE
    # ==========================================================

    if (
        "invoice" in text
        and has_any([
            "latest transaction",
            "last transaction",
            "recent transaction",
            "from transaction",
        ])
    ):
        return "invoice_from_transaction"

    if "invoice" in text:
        return "invoice"

    # ==========================================================
    # FINANCIAL ADVICE
    # ==========================================================

    if (
        has_any([
            "improve my spending",
            "spending advice",
            "budget advice",
            "save money",
            "reduce spending",
            "overspending",
        ])
    ):
        return "financial_advice"

    # ==========================================================
    # SPENDING PERIOD ANALYSIS
    # ==========================================================

    if (
        has_any(["monthly", "this month"])
        and has_any(["spending", "expense", "spend"])
    ):
        return "monthly_spending"

    if (
        has_any(["weekly", "this week"])
        and has_any(["spending", "expense", "spend"])
    ):
        return "weekly_spending"

    if (
        has_any(["daily", "today"])
        and has_any(["spending", "expense", "spend"])
    ):
        return "daily_spending"

    # ==========================================================
    # TRANSACTION INSIGHTS
    # ==========================================================

    if (
        has_any([
            "who do i pay",
            "top recipient",
            "largest transaction",
            "latest transaction",
            "recent transaction",
            "transaction history",
            "highest spending category",
            "most often",
        ])
    ):
        return "transaction_query"

    # ==========================================================
    # TOP CATEGORY
    # ==========================================================

    if (
        "category" in text
        and has_any([
            "top",
            "highest",
            "biggest",
            "most",
        ])
    ):
        return "top_category"


    # ==========================================================
    # TOP RECIPIENT
    # ==========================================================

    if (
        (
            "recipient" in text
            or "pay" in text
            or "payment" in text
        )
        and has_any([
            "top",
            "most",
            "frequent",
        ])
    ):
        return "top_recipient"

    # ==========================================================
    # GENERIC ANALYTICS
    # ==========================================================

    if (
        has_any([
            "analytics",
            "analysis",
            "spending",
            "expense",
            "budget",
            "insight",
            "summary",
        ])
    ):
        return "analytics"

    # ==========================================================
    # RECURRING CREATION
    # ==========================================================

    if (
        has_any([
            "recurring",
            "monthly payment",
            "weekly payment",
            "subscription",
        ])
    ):
        return "recurring"

    # ==========================================================
    # PAYMENT
    # ==========================================================

    if has_any([
        "pay",
        "send",
        "transfer",
    ]):
        return "payment"

    return "general"