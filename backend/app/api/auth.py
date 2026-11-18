import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    COOKIE_NAME,
    client_ip,
    current_user,
    make_session_token,
    verify_password,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.schemas import LoginIn, MeOut
from app.storage import users as users_store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=MeOut)
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limiter = request.app.state.login_limiter
    ip = client_ip(request)
    wait = limiter.retry_after(ip)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts, try again later",
            headers={"Retry-After": str(wait)},
        )
    # Always run the (slow) hash check so a wrong username isn't faster.
    pw_ok = verify_password(settings.app_password_hash, body.password)
    user_ok = hmac.compare_digest(body.username.strip().lower(), settings.app_username.lower())
    if not (pw_ok and user_ok):
        limiter.record_failure(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")
    limiter.reset(ip)
    user = users_store.get_or_create(db, settings.app_username)
    response.set_cookie(
        COOKIE_NAME,
        make_session_token(settings, user.id),
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return MeOut(username=user.username)


@router.post("/logout", status_code=204)
def logout(settings: Settings = Depends(get_settings)):
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, httponly=True)
    return response


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)):
    return MeOut(username=user.username)
