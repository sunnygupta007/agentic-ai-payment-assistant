import time
from collections import defaultdict, deque
from html import escape
from fastapi import HTTPException
from .config import get_settings


_hits: dict[str, deque[float]] = defaultdict(deque)


def sanitize_text(value: str, limit: int = 1200) -> str:
    cleaned = escape(value or "", quote=False).strip()
    return cleaned[:limit]


def enforce_rate_limit(session_id: str) -> None:
    settings = get_settings()
    now = time.time()
    bucket = _hits[session_id]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Too many requests for this session.")
    bucket.append(now)
