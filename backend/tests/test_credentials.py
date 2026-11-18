import pytest
from fastapi.testclient import TestClient

from app import credentials
from app.auth import verify_password
from app.config import get_settings
from tests.conftest import PASSWORD


def _settings(**update):
    return get_settings().model_copy(update=update)


def test_rejects_missing_and_placeholder_values(settings):
    with pytest.raises(RuntimeError, match="Set APP_PASSWORD"):
        credentials.resolve(_settings(app_password="", app_password_hash=""))
    with pytest.raises(RuntimeError, match="APP_PASSWORD must be"):
        credentials.resolve(_settings(app_password="short", app_password_hash=""))
    with pytest.raises(RuntimeError, match="APP_PASSWORD must be"):
        credentials.resolve(_settings(app_password="change-me-please", app_password_hash=""))
    with pytest.raises(RuntimeError, match="not a valid argon2"):
        credentials.resolve(_settings(app_password_hash="$argon2id$REPLACE_ME"))
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        credentials.resolve(_settings(secret_key="change-me-to-a-long-random-string"))


def test_plain_password_is_hashed(settings):
    s = _settings(app_password="hunter2hunter2", app_password_hash="")
    credentials.resolve(s)
    assert s.app_password_hash.startswith("$argon2")
    assert verify_password(s.app_password_hash, "hunter2hunter2")


def test_secret_generated_once_and_reused(settings, tmp_path):
    s1 = _settings(secret_key="", data_dir=tmp_path)
    credentials.resolve(s1)
    path = tmp_path / credentials.SECRET_FILE
    assert len(s1.secret_key) >= 32 and path.read_text().strip() == s1.secret_key
    assert path.stat().st_mode & 0o077 == 0  # owner-only
    s2 = _settings(secret_key="", data_dir=tmp_path)
    credentials.resolve(s2)
    assert s2.secret_key == s1.secret_key


def _client(s):
    from app.main import create_app

    return TestClient(create_app(s), headers={"X-Puffin": "1"})


def test_plain_password_login_survives_restart(settings, tmp_path):
    """Plain password + generated secret: a session from one start works after the next."""
    base = dict(app_password=PASSWORD, app_password_hash="", secret_key="", data_dir=tmp_path)
    with _client(_settings(**base)) as c1:
        assert c1.post("/api/auth/login", json={"username": "me", "password": "wrong"}).status_code == 401
        assert c1.post("/api/auth/login", json={"username": "me", "password": PASSWORD}).status_code == 200
        cookie = c1.cookies.get("puffin_session")
    with _client(_settings(**base)) as c2:  # new in-memory hash, same secret file
        c2.cookies.set("puffin_session", cookie)
        assert c2.get("/api/auth/me").status_code == 200
    with _client(_settings(**{**base, "app_password": "a-new-password"})) as c3:
        c3.cookies.set("puffin_session", cookie)
        assert c3.get("/api/auth/me").status_code == 401  # password change logs out
