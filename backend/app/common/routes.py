# app/common/routes.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.routers.auth import get_current_user, User

from app.common.schemas import ContentsResponse, MasterDataResponse
from app.common.service import build_contents, build_master_data, parse_keys

router = APIRouter(prefix="/common", tags=["Common"])


@router.get("/contents", response_model=ContentsResponse)
def get_contents(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """App-wide bootstrap data — call once after login and cache on the client.

    Replaces repeated `/auth/me` (+ basic learning stats) calls across pages.
    """
    return build_contents(session, current_user)


@router.get("/master-data", response_model=MasterDataResponse)
def get_master_data(
    keys: str | None = Query(
        default=None,
        description="Comma-separated lookup keys: topics,patterns,difficulties,languages",
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Lookup lists for dropdowns/selects. Returns only the requested (known) keys."""
    return build_master_data(session, parse_keys(keys))
