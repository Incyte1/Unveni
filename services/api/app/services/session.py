from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Literal

from fastapi import Depends, Request

from app.config import settings
from app.db import DatabaseSession, get_db_session
from app.errors import AppError, AuthenticationError
from app.models import SessionCreateRequest, SessionResponse, SessionUser
from app.repositories.audit import AuditRepository
from app.repositories.session import SessionRepository


@dataclass(frozen=True)
class AuthenticatedSessionContext:
    session_id: str
    user_id: str
    handle: str
    display_name: str
    entitlement: str
    execution_mode: Literal["paper", "live"]
    auth_provider: str
    expires_at: datetime
    mode: Literal["development", "authenticated"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value))


def _build_anonymous_session() -> SessionResponse:
    return SessionResponse(
        mode="anonymous",
        is_authenticated=False,
        user=None,
        entitlement=settings.default_entitlement,
        execution_mode=settings.default_execution_mode,
        session_strategy=settings.session_strategy,
        requires_local_token=settings.local_login_requires_token,
        expires_at=None
    )


def _display_name_for_handle(handle: str, display_name: str | None) -> str:
    if display_name and display_name.strip():
        return display_name.strip()
    parts = [part for part in handle.replace(".", "-").replace("_", "-").split("-") if part]
    return " ".join(part.capitalize() for part in parts) if parts else handle


def _context_mode() -> Literal["development", "authenticated"]:
    return "development" if settings.session_strategy == "development" else "authenticated"


def _to_context(row: dict[str, object]) -> AuthenticatedSessionContext:
    return AuthenticatedSessionContext(
        session_id=str(row["session_id"]),
        user_id=str(row["user_id"]),
        handle=str(row["handle"]),
        display_name=str(row["display_name"]),
        entitlement=str(row["entitlement"]),
        execution_mode=str(row["execution_mode"]),  # type: ignore[arg-type]
        auth_provider=str(row["auth_provider"]),
        expires_at=_parse_datetime(row["expires_at"]),
        mode=_context_mode()
    )


def build_session_response(
    session_context: AuthenticatedSessionContext | None
) -> SessionResponse:
    if session_context is None:
        return _build_anonymous_session()

    return SessionResponse(
        mode=session_context.mode,
        is_authenticated=True,
        user=SessionUser(
            id=session_context.user_id,
            handle=session_context.handle,
            name=session_context.display_name
        ),
        entitlement=session_context.entitlement,
        execution_mode=session_context.execution_mode,
        session_strategy=settings.session_strategy,
        requires_local_token=settings.local_login_requires_token,
        expires_at=session_context.expires_at
    )


def lookup_authenticated_session(
    session: DatabaseSession,
    request: Request
) -> AuthenticatedSessionContext | None:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        return None

    repository = SessionRepository(session)
    row = repository.find_session_by_token_hash(hash_session_token(raw_token))
    if row is None:
        return None

    expires_at = _parse_datetime(row["expires_at"])
    revoked_at = row["revoked_at"]
    is_active = bool(row["is_active"])

    if revoked_at or not is_active or expires_at <= utc_now():
        if not revoked_at and expires_at <= utc_now():
            repository.revoke_session(str(row["session_id"]))
        return None

    repository.touch_session(str(row["session_id"]))
    return _to_context(dict(row))


def create_session(
    session: DatabaseSession,
    request: Request,
    payload: SessionCreateRequest
) -> tuple[SessionResponse, str]:
    if settings.session_strategy == "external":
        raise AppError(
            code="session_creation_unavailable",
            message="Session creation is disabled until an external identity provider is connected.",
            status_code=503
        )

    if settings.local_login_requires_token:
        if not payload.access_token or payload.access_token != settings.local_auth_token:
            raise AuthenticationError(
                code="invalid_login_token",
                message="The supplied access token was rejected."
            )

    repository = SessionRepository(session)
    audit_repository = AuditRepository(session)

    handle = payload.handle.strip().lower()
    user = repository.upsert_local_user(
        handle=handle,
        display_name=_display_name_for_handle(handle, payload.display_name),
        entitlement=settings.default_entitlement,
        execution_mode=settings.default_execution_mode
    )

    raw_token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(hours=settings.session_ttl_hours)
    created_session = repository.create_session(
        user_id=str(user["id"]),
        token_hash=hash_session_token(raw_token),
        expires_at=expires_at.isoformat(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    context = _to_context(dict(created_session))
    audit_repository.record_event(
        event_type="auth.session.created",
        user_id=context.user_id,
        session_id=context.session_id,
        entity_type="session",
        entity_id=context.session_id,
        payload={
            "handle": context.handle,
            "session_strategy": settings.session_strategy
        }
    )
    return build_session_response(context), raw_token


def logout_session(session: DatabaseSession, request: Request) -> SessionResponse:
    active_session = lookup_authenticated_session(session, request)
    if active_session is None:
        return _build_anonymous_session()

    repository = SessionRepository(session)
    repository.revoke_session(active_session.session_id)
    AuditRepository(session).record_event(
        event_type="auth.session.revoked",
        user_id=active_session.user_id,
        session_id=active_session.session_id,
        entity_type="session",
        entity_id=active_session.session_id
    )
    return _build_anonymous_session()


def optional_authenticated_session(
    request: Request,
    session: DatabaseSession = Depends(get_db_session)
) -> AuthenticatedSessionContext | None:
    return lookup_authenticated_session(session, request)


def request_session(
    active_session: AuthenticatedSessionContext | None = Depends(optional_authenticated_session)
) -> SessionResponse:
    return build_session_response(active_session)


def require_authenticated_session(
    active_session: AuthenticatedSessionContext | None = Depends(optional_authenticated_session)
) -> AuthenticatedSessionContext:
    if active_session is None:
        raise AuthenticationError(
            code="unauthenticated",
            message="Sign in to access watchlists and paper trading."
        )
    return active_session
