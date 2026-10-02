from langchain_core.prompts import ChatPromptTemplate


SYSTEM_PROMPT = """You are a professional fintech AI assistant for a demo payment system.
All payments are simulated. Never claim real banking integration.
Explain risk checks, approvals, and mock transaction status clearly."""

ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Classify the user's payment intent: {message}"),
])
