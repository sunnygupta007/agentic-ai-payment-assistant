from langchain_core.tools import tool


@tool
def get_wallet_balance() -> str:
    """Return the demo wallet balance. Runtime service injects real session data."""
    return "Demo wallet balance is available through the payment service."


@tool
def list_transactions() -> str:
    """List recent simulated transactions."""
    return "Recent simulated transactions are available through analytics service."


@tool
def create_mock_transaction(recipient: str, amount: float) -> str:
    """Create a simulated transaction."""
    return f"Prepared simulated payment of INR {amount} to {recipient}."


@tool
def analyze_spending() -> str:
    """Analyze spending categories and trends."""
    return "Spending analysis is available as chart-ready JSON."


@tool
def generate_invoice(client: str, amount: float) -> str:
    """Generate a simulated invoice."""
    return f"Generated simulated invoice for {client}: INR {amount}."


@tool
def create_recurring_payment(recipient: str, amount: float, frequency: str) -> str:
    """Create a simulated recurring payment."""
    return f"Created {frequency} simulated recurring payment to {recipient}."


@tool
def detect_fraud_risk(amount: float, recipient: str) -> str:
    """Detect mock fraud risk."""
    return "High risk" if amount >= 10000 or "unknown" in recipient.lower() else "Low risk"


@tool
def request_approval(reason: str) -> str:
    """Request user approval for a risky simulated action."""
    return f"Approval requested: {reason}"


@tool
def log_audit_event(event: str) -> str:
    """Log an audit event."""
    return f"Audit logged: {event}"


PAYMENT_TOOLS = [
    get_wallet_balance,
    list_transactions,
    create_mock_transaction,
    analyze_spending,
    generate_invoice,
    create_recurring_payment,
    detect_fraud_risk,
    request_approval,
    log_audit_event,
]
