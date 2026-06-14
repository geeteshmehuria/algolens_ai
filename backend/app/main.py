# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Import routers
from app.routers import (
    auth,
    topics,
    problems,
    attempts,
    revision,
    roadmap,
    dashboard,
    ai,
    user_problems,
    topic_notes,
)

logger = logging.getLogger(__name__)

# Schema is managed by Alembic — run `alembic upgrade head` (or init_db.py for
# a fresh database) before starting the server.
app = FastAPI(
    title="AlgoLens AI API",
    description="Backend service for AlgoLens AI DSA learning platform.",
    version="1.0.0",
)

# Configure CORS from settings: FRONTEND_URL + CORS_ORIGINS always; localhost
# dev origins are added only outside production (see Settings.allowed_cors_origins).
allowed_origins = settings.allowed_cors_origins()
logger.info("Allowed CORS origins: %s", allowed_origins)

allow_origin_regex = settings.CORS_ORIGIN_REGEX if settings.CORS_ORIGIN_REGEX else None
if allow_origin_regex:
    logger.info("Allowed CORS origin regex: %s", allow_origin_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(topics.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(attempts.router, prefix="/api")
app.include_router(revision.router, prefix="/api")
app.include_router(roadmap.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(user_problems.router, prefix="/api")
app.include_router(topic_notes.router, prefix="/api")


@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "AlgoLens AI API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health")
def health():
    """Liveness probe for the hosting platform (Render health check).

    Intentionally does not touch the database so a transient DB blip does not
    flap the platform health check and recycle the instance.
    """
    return {"status": "ok"}
