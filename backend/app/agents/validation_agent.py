from ..utils import parse_amount, parse_recipient


def validate_payment_message(message: str) -> dict:
    amount = parse_amount(message)
    recipient = parse_recipient(message)
    missing = []
    if amount is None:
        missing.append("amount")
    if not recipient:
        missing.append("recipient")
    return {"valid": not missing, "missing": missing, "amount": amount or 0, "recipient": recipient}
