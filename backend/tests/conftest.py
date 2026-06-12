import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 — register all tables
from app.models import User, DSATopic, DSAPattern, DSAProblem


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def user(session):
    u = User(email="learner@test.dev", password_hash="x", full_name="Learner")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def make_problem(session):
    """Factory: creates a problem (plus its topic/pattern on demand)."""
    cache = {}

    def _make(
        title="Problem",
        topic="Arrays & Hashing",
        pattern="Hashing",
        difficulty="Easy",
        examples=None,
        description="desc",
    ):
        if topic not in cache:
            t = DSATopic(name=topic, description="")
            session.add(t)
            session.commit()
            session.refresh(t)
            p = DSAPattern(topic_id=t.id, name=pattern, description="")
            session.add(p)
            session.commit()
            session.refresh(p)
            cache[topic] = (t, p)
        t, p = cache[topic]
        problem = DSAProblem(
            title=title,
            difficulty=difficulty,
            topic_id=t.id,
            pattern_id=p.id,
            description=description,
            examples=examples or [],
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem

    return _make
