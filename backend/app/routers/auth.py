import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.core import get_settings
from app.session import (
    OAUTH_STATE_COOKIE,
    SESSION_COOKIE,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _cookie_secure(base_url: str) -> bool:
    return base_url.startswith("https://")


def _set_oauth_state_cookie(response: Response, state: str) -> None:
    settings = get_settings()
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=_cookie_secure(settings.app_base_url),
        samesite="lax",
        max_age=600,
        path="/",
    )


def _set_session_cookie(response: Response, email: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(email),
        httponly=True,
        secure=_cookie_secure(settings.app_base_url),
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


@router.get("/google/login")
def google_login() -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.app_base_url}{settings.google_redirect_path}"
    google_query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    google_url = f"https://accounts.google.com/o/oauth2/v2/auth?{google_query}"
    response = RedirectResponse(str(google_url))
    _set_oauth_state_cookie(response, state)
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
) -> RedirectResponse:
    settings = get_settings()
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not expected_state or not state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")

    redirect_uri = f"{settings.app_base_url}{settings.google_redirect_path}"
    token_response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    if token_response.status_code >= 400:
        logger.warning(
            "Google token exchange failed with status %s: %s",
            token_response.status_code,
            token_response.text[:500],
        )
        raise HTTPException(status_code=401, detail="Google token exchange failed")

    id_token = token_response.json().get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="Google token was missing identity")

    token_info = httpx.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": id_token},
        timeout=10,
    )
    if token_info.status_code >= 400:
        raise HTTPException(status_code=401, detail="Google identity validation failed")

    claims: dict[str, Any] = token_info.json()
    if claims.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Google token audience was invalid")

    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google account did not provide an email")

    response = RedirectResponse("/")
    _set_session_cookie(response, email)
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/auth/google/login")
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response
