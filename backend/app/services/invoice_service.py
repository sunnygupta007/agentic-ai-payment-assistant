from datetime import datetime
from pathlib import Path
from ..utils import new_transaction_id


def create_invoice_payload(client: str, amount: float, description: str) -> dict:
    invoice_id = f"INV-{new_transaction_id().split('-')[-1]}"
    return {
        "invoice_id": invoice_id,
        "client": client,
        "amount": amount,
        "description": description,
        "status": "generated",
        "created_at": datetime.utcnow().isoformat(),
        "note": "This simulated invoice was prepared by the demo AI assistant. No real invoice, tax document, or payment request was issued.",
        "download_hint": f"/api/invoice/{invoice_id}",
    }
