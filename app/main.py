import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import all models so SQLAlchemy's metadata knows about every table.
# This must happen before create_all is called in the lifespan.
import app.models  # noqa: F401

from app.config import get_settings
from app.database import engine, Base
from app.routes import auth, movies, ratings, recommendations, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    On startup: create any missing database tables (idempotent).
    On shutdown: cleanly dispose of the connection pool.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")
    yield
    await engine.dispose()
    logger.info("Database connection pool closed.")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-quality REST API for personalised film recommendations. "
        "Uses JWT authentication and content-based filtering via cosine similarity "
        "on genre vectors."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    # Restrict origins in production — e.g. allow_origins=["https://yourfrontend.com"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(ratings.router)
app.include_router(recommendations.router)
app.include_router(users.router)


@app.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": "1.0.0"}


# Serve the frontend — mounted last so API routes always take precedence
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
