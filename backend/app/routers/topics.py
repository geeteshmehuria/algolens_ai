# app/routers/topics.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List

from app.database import get_session
from app.models import DSATopic, DSAPattern

router = APIRouter(tags=["Topics & Patterns"])


@router.get("/topics", response_model=List[DSATopic])
def get_topics(
    category: str | None = None,
    session: Session = Depends(get_session),
):
    """Retrieve all DSA topics, ordered by curriculum learning_order.

    Optional ?category= filters to a single curriculum category. Topics without
    a learning_order (legacy/unreconciled) sort last by name."""
    statement = select(DSATopic)
    if category:
        statement = statement.where(DSATopic.category == category)
    statement = statement.order_by(
        DSATopic.learning_order.is_(None), DSATopic.learning_order, DSATopic.name
    )
    return session.exec(statement).all()


@router.get("/patterns", response_model=List[DSAPattern])
def get_patterns(session: Session = Depends(get_session)):
    """Retrieve all DSA patterns"""
    return session.exec(select(DSAPattern)).all()
