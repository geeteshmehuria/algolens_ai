# app/routers/auth.py
import hashlib
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timedelta
from typing import List, Optional

from app.config import settings
from app.database import get_session
from app.models import User, Role, UserRole, PasswordResetToken
from app.services.email_service import send_password_reset_email
from app.utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """Emails are matched with exact equality in the DB, so they must be
    stored and looked up in one canonical form (RFC allows a case-sensitive
    local part, but treating it that way locks users out)."""
    return email.strip().lower()


def _validate_password_bytes(password: str) -> str:
    # bcrypt 5.x raises on inputs over 72 bytes instead of truncating
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return password


# --- Pydantic Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    _check_password = field_validator("password")(_validate_password_bytes)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return _validate_password_bytes(v)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    leetcode_username: Optional[str] = None
    created_on: datetime

    class Config:
        from_attributes = True


class MeResponse(UserResponse):
    roles: List[str] = []


# --- Authentication Dependency ---
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    """Dependency to validate JWT and get current logged-in user"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_user_role_names(session: Session, user_id: int) -> List[str]:
    return list(
        session.exec(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        ).all()
    )


def require_admin(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    """Dependency for content-management endpoints. Grant the role with:
    python make_admin.py your@email.com"""
    if "admin" not in get_user_role_names(session, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action.",
        )
    return current_user


# --- Endpoints ---
@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_data: UserRegister, session: Session = Depends(get_session)):
    """Register a new user"""
    email = normalize_email(user_data.email)
    # Check if user already exists
    statement = select(User).where(User.email == email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # Create new user
    new_user = User(
        email=email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, session: Session = Depends(get_session)):
    """Authenticate user and return JWT access token"""
    statement = select(User).where(User.email == normalize_email(credentials.email))
    user = session.exec(statement).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


GENERIC_RESET_MESSAGE = (
    "If an account exists for this email, a reset link has been sent."
)


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    """Issue a password-reset token. Always returns the same generic message
    so the response never reveals whether the email is registered."""
    email = normalize_email(payload.email)
    user = session.exec(select(User).where(User.email == email)).first()

    if user:
        now = datetime.utcnow()
        # Throttle: if a token was issued in the last 60s, silently reuse the
        # generic response without creating another one.
        recent = session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.created_on > now - timedelta(seconds=60),
            )
        ).first()
        if not recent:
            # Invalidate any older unused tokens for this user
            stale_tokens = session.exec(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_on == None,  # noqa: E711
                )
            ).all()
            for stale in stale_tokens:
                stale.used_on = now
                session.add(stale)

            raw_token = secrets.token_urlsafe(32)  # 256 bits of entropy
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_on=now + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
                created_ip=request.client.host if request.client else None,
                user_agent=(request.headers.get("user-agent") or "")[:255] or None,
            )
            session.add(reset_token)
            session.commit()

            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
            try:
                send_password_reset_email(user.email, reset_link)
            except Exception as exc:
                # Caller still gets the generic message (no enumeration), but
                # ops needs the real failure. SMTP errors carry server replies,
                # never our link/token, so logging exc is safe.
                logger.error(
                    "Password reset email to %s failed: %s: %s",
                    user.email,
                    type(exc).__name__,
                    exc,
                )

    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest, session: Session = Depends(get_session)
):
    """Set a new password using a valid, unexpired, unused reset token."""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    reset_token = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).first()

    now = datetime.utcnow()
    invalid = (
        not reset_token
        or reset_token.used_on is not None
        or reset_token.expires_on < now
    )
    if invalid:
        # One message for missing/expired/used — no oracle for attackers
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    user = session.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    user.password_hash = hash_password(payload.new_password)
    reset_token.used_on = now
    session.add(user)
    session.add(reset_token)
    session.commit()

    return {"message": "Password has been reset successfully. Please log in."}


@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retrieve details (including roles) of the currently authenticated user"""
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        leetcode_username=current_user.leetcode_username,
        created_on=current_user.created_on,
        roles=get_user_role_names(session, current_user.id),
    )
