# app/common/schemas.py
"""Schemas for the common bootstrap (`/common/contents`) and lookup
(`/common/master-data`) endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ContentsUser(BaseModel):
    id: int
    name: Optional[str] = None
    email: str
    roles: List[str] = []
    permissions: List[str] = []


class ContentsResponse(BaseModel):
    """Stable, app-wide data fetched once after login and cached on the client.

    Deliberately small: no big lists (use /master-data), no secrets, no token.
    """

    user: ContentsUser
    preferences: Dict[str, Any] = {}
    feature_flags: Dict[str, bool] = {}
    app_config: Dict[str, Any] = {}
    learning_summary: Dict[str, Any] = {}
    # ISO timestamp the client can use to decide whether to refetch.
    version: str


class TopicOption(BaseModel):
    id: int
    name: str


class PatternOption(BaseModel):
    id: int
    name: str
    topic_id: int


class MasterDataResponse(BaseModel):
    """Lookup lists for dropdowns/selects. Only the requested keys are populated;
    everything else stays ``None`` so the payload carries just what the page asked for."""

    topics: Optional[List[TopicOption]] = None
    patterns: Optional[List[PatternOption]] = None
    difficulties: Optional[List[str]] = None
    languages: Optional[List[str]] = None
