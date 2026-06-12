# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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

# Schema is managed by Alembic — run `alembic upgrade head` (or init_db.py for
# a fresh database) before starting the server.
app = FastAPI(
    title="AlgoLens AI API",
    description="Backend service for AlgoLens AI DSA learning platform.",
    version="1.0.0",
)

# Configure CORS
# In production, this should only allow the frontend URL.
# In development, it allows localhost:5173 (SvelteKit default dev server).
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
