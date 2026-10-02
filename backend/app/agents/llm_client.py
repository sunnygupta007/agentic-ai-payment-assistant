from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx

from langchain_core.messages import SystemMessage, HumanMessage

from ..config import get_settings

SYSTEM_PROMPT = """
You are Agentic AI Payment Assistant.

This application is a hackathon demo.

All payments, invoices, wallet balances, approvals and transactions are simulated.

Your responsibilities:

- Help users make simulated payments
- Explain payment status
- Explain fraud checks
- Explain spending analytics
- Explain invoices
- Explain recurring payments
- Explain wallet balances

You are NOT a general purpose chatbot.

If the user asks for something unrelated to payments, finance, spending, transactions, invoices, budgeting or wallets:

Politely redirect them back to payment-related tasks.

DO NOT answer the question.

Instead respond:

"I am an Agentic AI Payment Assistant and can only help with payments, wallets, invoices, fraud checks, budgeting and financial insights."

Example:

User: Buy me a Netflix subscription

Assistant:
I cannot purchase subscriptions in this demo.
I can help simulate payments, manage wallets, create invoices, review spending and analyze transactions.

Never claim to move real money.
Never tell users to use Google Pay, PhonePe, Paytm or bank apps.
Always assume this is a simulated payment environment.
"""



try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None


def get_chat_model(streaming: bool = True):
    settings = get_settings()

    if not settings.llm_api_key or ChatOpenAI is None:
        return None

    async_client = httpx.AsyncClient(
        timeout=60.0,
    )

    return ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    streaming=streaming,
    temperature=1,
    http_async_client=async_client,
)


async def stream_llm_or_fallback(
    prompt: str,
    fallback: str,
) -> AsyncGenerator[str, None]:

    model = get_chat_model(streaming=True)

    if not model:
        for token in fallback.split(" "):
            yield token + " "
        return

    try:
        # async for chunk in model.astream(prompt):
        #     if chunk.content:
        #         yield str(chunk.content)
        messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

        async for chunk in model.astream(messages):
            if chunk.content:
                yield str(chunk.content)

    except Exception as e:
        print(f"LLM ERROR: {e}")

        yield (
            "⚠️ AI service temporarily unavailable. "
            "Please verify endpoint configuration."
        )