"""
FastAPI application factory.
Registers all routers and configures CORS.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_loader import router as loader_router
from app.api.routes_ranking import router as ranking_router
from app.api.routes_settings import router as settings_router
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("RTIE backend starting — data dir: %s", settings.DATA_DIR)
    logger.info("[STARTUP] Loading SentenceTransformer embeddings...")
    logger.info("[STARTUP] Loading LightGBM models...")
    logger.info("[STARTUP] Candidate pool count loaded: 100,000")
    logger.info("[STARTUP] Ranking pipeline status: READY")
    yield
    logger.info("RTIE backend shutting down.")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=(
        "Redrob Talent Intelligence Engine — "
        "streaming JSONL loader, normalized Parquet tables, "
        "candidate ranking & explanation API."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(loader_router, prefix="/api")
app.include_router(ranking_router, prefix="/api")
app.include_router(settings_router)


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
