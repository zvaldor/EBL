import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from aiogram.types import Update

from app.config import settings
from app.bot.setup import create_bot, create_dispatcher
from app.db.session import engine
from app.db.base import Base
from app.db.models.config import PointConfig, DEFAULT_CONFIG
from app.db.session import AsyncSessionLocal
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = create_bot()
dp = create_dispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (use alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default point config
    async with AsyncSessionLocal() as db:
        for key, (value, description) in DEFAULT_CONFIG.items():
            q = await db.execute(select(PointConfig).where(PointConfig.key == key))
            if not q.scalar_one_or_none():
                db.add(PointConfig(key=key, value=value, description=description))
        await db.commit()

    # Set webhook (skip if WEBHOOK_HOST not configured yet)
    if settings.WEBHOOK_HOST:
        webhook_url = f"{settings.WEBHOOK_HOST}/webhook/{settings.WEBHOOK_SECRET}"
        try:
            await bot.set_webhook(
                url=webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,
            )
            logger.info(f"Webhook set to {webhook_url}")
        except Exception as e:
            logger.warning(f"Failed to set webhook: {e}")
    else:
        logger.warning("WEBHOOK_HOST not set — webhook not configured")

    yield

    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(title="EBL API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
from app.api.routes import leaderboard, visits, baths, users, settings as settings_router

app.include_router(leaderboard.router, prefix="/api")
app.include_router(visits.router, prefix="/api")
app.include_router(baths.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.post(f"/webhook/{settings.WEBHOOK_SECRET}")
async def webhook(request: Request) -> Response:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend SPA
# In Docker: /app/frontend/dist (copied by multi-stage build)
# In dev: ../../frontend/dist (relative to backend/app/)
frontend_dist = os.environ.get(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"),
)
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/app/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/app")
    async def serve_spa_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))
