# app/routers/topics.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List

from app.database import get_session
from app.models import DSATopic, DSAPattern

router = APIRouter(tags=["Topics & Patterns"])


@router.get("/topics", response_model=List[DSATopic])
def get_topics(session: Session = Depends(get_session)):
    """Retrieve all DSA topics"""
    return session.exec(select(DSATopic)).all()


@router.get("/patterns", response_model=List[DSAPattern])
def get_patterns(session: Session = Depends(get_session)):
    """Retrieve all DSA patterns"""
    return session.exec(select(DSAPattern)).all()
