"""Single-user auth: argon2 hash from env, signed session cookie, login rate limit."""

import hashlib
import hmac
import threading
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import User
from app.storage import users as users_store

COOKIE_NAME = "puffin_session"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _password_fingerprint(settings: Settings) -> str:
    # Changing the password (or SECRET_KEY) invalidates every existing session.
    # Keyed with the secret because the cookie payload is readable. Uses the
    # plain password when given, since its in-memory hash changes every restart.
    credential = settings.app_password or settings.app_password_hash
    return hmac.new(settings.secret_key.encode(), credential.encode(), hashlib.sha256).hexdigest()[:16]


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="puffin-session")


def make_session_token(settings: Settings, user_id: int) -> str:
    return _serializer(settings).dumps({"uid": user_id, "pw": _password_fingerprint(settings)})


def read_session_token(settings: Settings, token: str) -> int | None:
    try:
        data = _serializer(settings).loads(token, max_age=settings.session_days * 86400)
    except BadSignature:
        return None
    if not isinstance(data, dict) or data.get("pw") != _password_fingerprint(settings):
        return None
    uid = data.get("uid")
    return uid if isinstance(uid, int) else None


class LoginRateLimiter:
    """In-memory sliding window of failed attempts per client IP."""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._fails: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._fails[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        return q

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds until another attempt is allowed; 0 if allowed now."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._prune(key, now)
            if len(q) < self.max_failures:
                return 0
            return max(1, int(q[0] + self.window - now) + 1)

    def record_failure(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


def client_ip(request: Request) -> str:
    # uvicorn --proxy-headers rewrites request.client from X-Forwarded-For
    # when the proxy is listed in FORWARDED_ALLOW_IPS.
    return request.client.host if request.client else "unknown"


def current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    uid = read_session_token(settings, token) if token else None
    user = users_store.get(db, uid) if uid is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user
