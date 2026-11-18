"""FastAPI app factory. JSON API under /api; the built SPA is served from STATIC_DIR."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from argon2 import extract_parameters
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import auth as auth_api
from app.api import entries as entries_api
from app.api import settings as settings_api
from app.auth import LoginRateLimiter
from app.config import Settings, get_settings
from app.db import get_engine
from app.storage import Conflict, Invalid, NotFound
from app.storage import users as users_store

log = logging.getLogger("puffin")

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-puffin"


def _check_settings(settings: Settings) -> None:
    problems = []
    if len(settings.secret_key) < 32 or "change-me" in settings.secret_key:
        problems.append("SECRET_KEY must be set to a random value of at least 32 characters")
    try:
        extract_parameters(settings.app_password_hash)
    except Exception:
        problems.append("APP_PASSWORD_HASH must be an argon2 hash (python -m app.cli hash-password)")
    if problems:
        raise RuntimeError("; ".join(problems))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _check_settings(settings)
        with Session(get_engine()) as db:
            users_store.get_or_create(db, settings.app_username)
        log.info("Puffin Journal ready (TZ=%s)", settings.tz)
        yield

    app = FastAPI(title="Puffin Journal", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.login_limiter = LoginRateLimiter(
        settings.login_max_failures, settings.login_window_seconds
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        # CSRF: state-changing API calls must carry a custom header, which a
        # cross-site form or simple request cannot set (no CORS is enabled).
        if (
            request.url.path.startswith("/api/")
            and request.method not in SAFE_METHODS
            and request.headers.get(CSRF_HEADER) != "1"
        ):
            return JSONResponse({"detail": "Missing X-Puffin header"}, status_code=403)
        response = await call_next(request)
        h = response.headers
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/api/"):
            h.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(NotFound)
    async def _nf(_: Request, exc: NotFound):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(Invalid)
    async def _inv(_: Request, exc: Invalid):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(Conflict)
    async def _conf(_: Request, exc: Conflict):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.get("/api/health", tags=["meta"])
    def health():
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(auth_api.router, prefix="/api")
    app.include_router(entries_api.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")

    _mount_spa(app, settings.static_dir)
    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    index = static_dir / "index.html"
    if not index.exists():
        return
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    root = static_dir.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
