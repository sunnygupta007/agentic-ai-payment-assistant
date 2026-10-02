import re
import uuid


def new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


def new_transaction_id() -> str:
    return f"TXN-{uuid.uuid4().hex[:10].upper()}"


def parse_amount(message: str) -> float | None:
    match = re.search(r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]+)?)", message, re.I)
    return float(match.group(1).replace(",", "")) if match else None


def parse_recipient(message: str) -> str:
    patterns = [r"\bto\s+([A-Za-z][A-Za-z0-9 _.-]{1,60})", r"\bfor\s+([A-Za-z][A-Za-z0-9 _.-]{1,60})"]
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            return match.group(1).strip().rstrip(".")
    return "Demo Recipient"
