from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import db as db_module
from app.auth import hash_password
from app.config import Settings, get_settings
from app.db import make_engine
from app.storage import users as users_store

BACKEND = Path(__file__).resolve().parent.parent
PASSWORD = "correct horse battery"


def migrate(url: str) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


@pytest.fixture
def db_url(tmp_path) -> str:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrate(url)
    return url


@pytest.fixture
def db(db_url):
    engine = make_engine(db_url)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def user_id(db) -> int:
    return users_store.get_or_create(db, "me").id


@pytest.fixture
def other_user_id(db) -> int:
    return users_store.get_or_create(db, "someone-else").id


@pytest.fixture(scope="session")
def password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def settings(db_url, tmp_path, password_hash, monkeypatch) -> Settings:
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("APP_USERNAME", "me")
    monkeypatch.setenv("APP_PASSWORD_HASH", password_hash)
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "no-static"))
    monkeypatch.setenv("TZ", "Europe/Berlin")
    get_settings.cache_clear()
    db_module.reset_engine()
    yield get_settings()
    get_settings.cache_clear()
    db_module.reset_engine()


@pytest.fixture
def client(settings):
    from app.main import create_app

    with TestClient(create_app(settings), headers={"X-Puffin": "1"}) as c:
        yield c


@pytest.fixture
def authed(client):
    r = client.post("/api/auth/login", json={"username": "me", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client
