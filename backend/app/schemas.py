from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str
    user_id: int


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=1200)


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class TransactionCreate(BaseModel):
    session_id: str
    recipient: str = Field(min_length=1, max_length=160)
    amount: float = Field(gt=0)
    category: str = "Transfer"
    method: str = "UPI"


class ApprovalDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")


class RecurringCreate(BaseModel):
    session_id: str
    recipient: str
    amount: float = Field(gt=0)
    frequency: str = "weekly"


class InvoiceCreate(BaseModel):
    session_id: str
    client: str = "Demo Client"
    amount: float = Field(gt=0)
    description: str = "Professional services"


class WalletTopUp(BaseModel):
    session_id: str
    amount: float = Field(gt=0, le=100000)
    source: str = Field(default="ui", max_length=40)
