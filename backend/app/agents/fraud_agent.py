from ..services.payment_service import assess_risk


async def fraud_check(amount: float, recipient: str) -> dict:
    score, level = await assess_risk(amount, recipient)
    return {"score": score, "level": level}
