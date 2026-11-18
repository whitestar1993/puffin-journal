"""Resolve login credentials and the session secret at startup.

- Password: APP_PASSWORD (plain, hashed in memory at startup) or
  APP_PASSWORD_HASH (argon2, from `python -m app.cli hash-password`).
- SECRET_KEY: optional. If unset, a random key is generated on first start and
  kept in DATA_DIR/secret_key so sessions survive restarts.
"""

import logging
import os
import secrets
from pathlib import Path

from argon2 import extract_parameters

from app.auth import hash_password
from app.config import Settings

log = logging.getLogger("puffin")

SECRET_FILE = "secret_key"
MIN_PASSWORD = 8


def _load_or_create_secret(data_dir: Path) -> str:
    path = data_dir / SECRET_FILE
    try:
        key = path.read_text().strip()
        if len(key) >= 32:
            return key
    except FileNotFoundError:
        pass
    key = secrets.token_urlsafe(48)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    log.warning("Generated a new session secret in %s", path)
    return key


def resolve(settings: Settings) -> None:
    """Validate credentials and fill in derived values. Raises RuntimeError."""
    problems: list[str] = []

    if settings.app_password_hash:
        try:
            extract_parameters(settings.app_password_hash)
        except Exception:
            problems.append("APP_PASSWORD_HASH is not a valid argon2 hash")
    elif settings.app_password:
        if len(settings.app_password) < MIN_PASSWORD or "change-me" in settings.app_password:
            problems.append(f"APP_PASSWORD must be at least {MIN_PASSWORD} characters (and not the example)")
    else:
        problems.append("Set APP_PASSWORD in .env")

    if settings.secret_key:
        if len(settings.secret_key) < 32 or "change-me" in settings.secret_key:
            problems.append("SECRET_KEY must be at least 32 random characters, or leave it empty")

    if problems:
        raise RuntimeError("; ".join(problems))

    if not settings.app_password_hash:
        # Hash once so login uses the same slow, constant-time argon2 check.
        settings.app_password_hash = hash_password(settings.app_password)
    if not settings.secret_key:
        settings.secret_key = _load_or_create_secret(settings.data_dir)
