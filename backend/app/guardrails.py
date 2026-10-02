from dataclasses import dataclass


BLOCKED_PHRASES = (
    "ignore previous instructions",
    "reveal system prompt",
    "bypass safety",
    "show hidden prompts",
)


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""


def check_prompt_injection(message: str) -> GuardrailResult:
    lowered = message.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in lowered:
            return GuardrailResult(False, f"Blocked prompt-injection phrase: {phrase}")
    return GuardrailResult(True)


def transaction_needs_approval(amount: float, recipient: str, risk_score: float) -> tuple[bool, str]:
    if amount >= 10000:
        return True, "Large transfer amount requires explicit approval."
    if "unknown" in recipient.lower() or "account" in recipient.lower():
        return True, "Unknown recipient requires approval."
    if risk_score >= 0.7:
        return True, "Suspicious pattern detected by fraud agent."
    return False, ""
