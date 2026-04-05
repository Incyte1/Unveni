from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.config import settings
from app.db import DatabaseSession, get_db_session
from app.models import SessionCreateRequest, SessionResponse
from app.services.session import create_session, logout_session, request_session

router = APIRouter(tags=["session"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="lax",
        max_age=settings.session_ttl_hours * 60 * 60,
        path="/"
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.use_secure_cookies,
        samesite="lax",
        path="/"
    )


@router.get("/session", response_model=SessionResponse)
def session_snapshot(
    session: SessionResponse = Depends(request_session)
) -> SessionResponse:
    return session


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def session_create(
    payload: SessionCreateRequest,
    request: Request,
    response: Response,
    session: DatabaseSession = Depends(get_db_session)
) -> SessionResponse:
    session_response, token = create_session(session, request, payload)
    set_session_cookie(response, token)
    return session_response


@router.post("/session/logout", response_model=SessionResponse)
def session_logout(
    request: Request,
    response: Response,
    session: DatabaseSession = Depends(get_db_session)
) -> SessionResponse:
    session_response = logout_session(session, request)
    clear_session_cookie(response)
    return session_response
