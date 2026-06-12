# app/database.py
from sqlmodel import create_engine, Session
from app.config import settings

# Create engine
# If using PostgreSQL, standard connection is fine.
# pool_pre_ping is useful to prevent stale connections.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def get_session():
    """Dependency helper for FastAPI routes to get DB session"""
    with Session(engine) as session:
        yield session
