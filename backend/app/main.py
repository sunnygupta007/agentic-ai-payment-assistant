from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api import analytics, approvals, auth, chat, dashboard, transactions, wallet
from .config import get_settings
from .db import SessionLocal, init_db
from .seed import seed_demo
from .websocket.routes import router as websocket_router


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(approvals.router)
app.include_router(analytics.router)
app.include_router(wallet.router)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    async with SessionLocal() as db:
        await seed_demo(db)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


frontend = Path(settings.frontend_dir)
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
