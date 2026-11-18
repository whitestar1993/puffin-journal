from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.auth import LoginRateLimiter
from app.timeutil import today
from tests.conftest import PASSWORD


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_endpoints_require_login(client):
    for path in ["/api/today", "/api/entries", "/api/tags", "/api/prompts", "/api/days/2026-01-01"]:
        assert client.get(path).status_code == 401, path


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": "me", "password": "nope"})
    assert r.status_code == 401


def test_login_rate_limited(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "me", "password": "nope"})
    r = client.post("/api/auth/login", json={"username": "me", "password": PASSWORD})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_rate_limiter_window():
    rl = LoginRateLimiter(max_failures=2, window_seconds=60)
    rl.record_failure("ip", now=0)
    rl.record_failure("ip", now=10)
    assert rl.retry_after("ip", now=20) == 41
    assert rl.retry_after("ip", now=61) == 0  # first failure expired
    assert rl.retry_after("other", now=20) == 0


def test_csrf_header_required(authed):
    r = authed.put("/api/entries/2026-01-01", json={"mood": 3}, headers={"X-Puffin": ""})
    assert r.status_code == 403


def test_session_cookie_flags(client):
    r = client.post("/api/auth/login", json={"username": "me", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_logout(authed):
    assert authed.get("/api/auth/me").json() == {"username": "me"}
    assert authed.post("/api/auth/logout").status_code == 204
    assert authed.get("/api/auth/me").status_code == 401


def test_tampered_cookie_rejected(authed):
    authed.cookies.set("puffin_session", authed.cookies.get("puffin_session")[:-2] + "xx")
    assert authed.get("/api/auth/me").status_code == 401


def test_checkin_flow(authed):
    t = authed.get("/api/today").json()["today"]
    day = authed.get(f"/api/days/{t}").json()
    assert day["entry"] is None and day["prompt"]["text"]
    tags = authed.get("/api/tags").json()
    body = {
        "mood": 4,
        "energy": 3,
        "tag_ids": [tags[0]["id"]],
        "prompt_id": day["prompt"]["id"],
        "prompt_answer": "Fresh air",
    }
    r = authed.put(f"/api/entries/{t}", json=body)
    assert r.status_code == 201
    assert r.json()["prompt_text"] == day["prompt"]["text"]
    assert authed.put(f"/api/entries/{t}", json={"mood": 5}).status_code == 200
    day = authed.get(f"/api/days/{t}").json()
    assert day["entry"]["mood"] == 5
    assert authed.get("/api/tags").json()[0]["usage"] == 0  # tags cleared by replace


def test_future_entry_rejected(authed):
    t = datetime.fromisoformat(authed.get("/api/today").json()["today"]).date()
    r = authed.put(f"/api/entries/{t + timedelta(days=1)}", json={"mood": 3})
    assert r.status_code == 422


def test_invalid_mood_rejected(authed):
    assert authed.put("/api/entries/2026-01-01", json={"mood": 7}).status_code == 422
    assert authed.put("/api/entries/2026-01-01", json={}).status_code == 422


def test_history_filters(authed):
    tags = {t["name"]: t["id"] for t in authed.get("/api/tags").json()}
    authed.put("/api/entries/2026-01-01", json={"mood": 2, "note": "rainy", "tag_ids": [tags["work"]]})
    authed.put("/api/entries/2026-01-02", json={"mood": 4, "note": "sunny walk"})
    assert [e["date"] for e in authed.get("/api/entries").json()] == ["2026-01-02", "2026-01-01"]
    assert [e["mood"] for e in authed.get("/api/entries", params={"q": "SUNNY"}).json()] == [4]
    assert [e["mood"] for e in authed.get("/api/entries", params={"tag": tags["work"]}).json()] == [2]
    assert authed.delete("/api/entries/2026-01-01").status_code == 204
    assert authed.get("/api/entries/2026-01-01").status_code == 404


def test_tag_and_prompt_management(authed):
    r = authed.post("/api/tags", json={"name": "Reading"})
    assert r.status_code == 201 and r.json()["name"] == "reading"
    assert authed.post("/api/tags", json={"name": "reading"}).status_code == 409
    tid = r.json()["id"]
    assert authed.patch(f"/api/tags/{tid}", json={"name": "books"}).json()["name"] == "books"
    assert authed.delete(f"/api/tags/{tid}").json() == {"result": "deleted"}
    p = authed.post("/api/prompts", json={"text": "Best moment?", "quick_answers": ["a"]}).json()
    assert authed.patch(f"/api/prompts/{p['id']}", json={"active": False}).json()["active"] is False
    assert authed.delete(f"/api/prompts/{p['id']}").status_code == 204
    assert authed.delete(f"/api/prompts/{p['id']}").status_code == 404


def test_today_uses_configured_timezone():
    # 23:30 UTC on Nov 17 is already Nov 18 in Berlin, still Nov 17 in New York.
    now = datetime(2026, 11, 17, 23, 30, tzinfo=timezone.utc)
    assert str(today(ZoneInfo("Europe/Berlin"), now)) == "2026-11-18"
    assert str(today(ZoneInfo("America/New_York"), now)) == "2026-11-17"


def test_startup_rejects_placeholder_config(settings):
    import pytest

    from app.main import _check_settings

    bad = settings.model_copy(
        update={
            "secret_key": "change-me-to-a-long-random-string",
            "app_password_hash": "$argon2id$v=19$m=65536,t=3,p=4$REPLACE_ME",
        }
    )
    with pytest.raises(RuntimeError) as exc:
        _check_settings(bad)
    assert "SECRET_KEY" in str(exc.value) and "APP_PASSWORD_HASH" in str(exc.value)
    _check_settings(settings)  # the real test config is accepted
