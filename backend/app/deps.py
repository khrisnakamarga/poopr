import base64
import json

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import get_settings
from app.database import get_db
from app.models import Profile, User
from app.session import SESSION_COOKIE, read_session_token


def email_from_easy_auth(
    principal_name: str | None,
    principal_id: str | None,
    principal: str | None,
) -> str:
    if principal_name:
        return principal_name.strip().lower()

    if principal:
        try:
            payload = json.loads(base64.b64decode(principal))
            claims = payload.get("claims", [])
        except (ValueError, TypeError, json.JSONDecodeError):
            claims = []

        for claim_type in (
            "preferred_username",
            "emails",
            "email",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn",
        ):
            for claim in claims:
                if claim.get("typ") == claim_type and claim.get("val"):
                    return str(claim["val"]).strip().lower()

    if principal_id:
        return f"{principal_id}@easy-auth.local".strip().lower()

    raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user(
    poopr_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    x_user_email: str | None = Header(default=None),
    x_ms_client_principal_name: str | None = Header(default=None),
    x_ms_client_principal_id: str | None = Header(default=None),
    x_ms_client_principal: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    session_email = read_session_token(poopr_session)
    if session_email:
        email = session_email
    elif settings.auth_mode == "easy_auth":
        email = email_from_easy_auth(
            x_ms_client_principal_name,
            x_ms_client_principal_id,
            x_ms_client_principal,
        )
    else:
        email = (x_user_email or "demo@poopr.local").strip().lower()

    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user

    display_name = email.split("@")[0].replace(".", " ").replace("_", " ").title() or "Poopr"
    user = User(email=email)
    profile = Profile(user=user, display_name=display_name)
    db.add(user)
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.scalar(select(User).where(User.email == email))
        if user:
            return user
        raise
    db.refresh(user)
    return user

