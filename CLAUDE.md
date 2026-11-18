# CLAUDE.md

**Start every session by reading [PLAN.md](PLAN.md).** When you finish a piece of
work, tick it off there (and add notes on anything that changed). The original
brief is in [SPEC.md](SPEC.md).

## What this is

Puffin Journal: a self-hosted, single-user daily mood journal. The core design
goal is a check-in that takes under 30 seconds, mostly taps. One Docker
container: FastAPI serves a JSON API under `/api` and the built Svelte SPA.

## ⚠️ Sensitive data

This app stores private mental-health-adjacent data. Hard rules:

- **No third-party calls**: no CDNs, web fonts, analytics, error trackers, or
  external APIs. All assets are bundled. The only planned exception is the
  user-configured ntfy server for reminders (Phase 4), and its messages must
  never include entry content.
- **Never log entry content** (mood, notes, answers, tags, search queries).
  Don't log request bodies. Access logging is off by default because search
  terms are in query strings.
- Keep the strict CSP in `app/main.py` intact.

## Layout

```
backend/
  app/
    main.py        app factory, security middleware (CSRF header, CSP), SPA serving
    config.py      env settings (pydantic-settings)
    auth.py        argon2 verify, signed session cookie, LoginRateLimiter, current_user
    db.py          engine (SQLite WAL, foreign keys on), get_db dependency
    models.py      SQLAlchemy models
    schemas.py     Pydantic request/response models
    storage/       THE ONLY MODULE THAT TOUCHES THE DB (entries, tags, prompts, users)
    api/           thin routers: auth.py, entries.py (today/days/entries), settings.py (tags/prompts)
    timeutil.py    today() in configured TZ
    credentials.py startup: plain APP_PASSWORD → in-memory hash; SECRET_KEY auto-generated to DATA_DIR/secret_key
    cli.py         hash-password, secret-key (optional helpers)
  alembic/versions/  migrations
  tests/           pytest (storage, API, rotation, TZ)
frontend/          Svelte 5 + Vite + TS, no SvelteKit
  src/lib/         api.ts (fetch client), router.svelte.ts (hash router), dates.ts, mood.ts
  src/routes/      Login, CheckIn, History, Settings
  src/components/  Scale, TagChips, PromptCard
docker/entrypoint.sh   runs `alembic upgrade head`, then uvicorn
Dockerfile             frontend → backend-build → (test) → runtime
```

## Data model

- `users(id, username, created_at)` — one row, created from `APP_USERNAME` at startup with default tags/prompts. The password lives in env (`APP_PASSWORD` or `APP_PASSWORD_HASH`), not the DB.
- `entries(id, user_id, date, mood 1-5, energy 1-5?, sleep 1-5?, prompt_id?, prompt_text?, prompt_answer?, note?, created_at, updated_at)` — unique `(user_id, date)`. Only mood is required.
  - `prompt_text` is a snapshot taken when the prompt is first answered; editing/deleting the prompt never rewrites history. A skipped prompt stores nothing.
- `tags(id, user_id, name, archived)` — unique `(user_id, name)`, names lowercased. Deleting a used tag archives it.
- `entry_tags(entry_id, tag_id)`.
- `prompts(id, user_id, text, quick_answers JSON, active)`. Daily prompt = active prompts sorted by id, index `date.toordinal() % n`.

## Conventions

- All DB access goes through `app/storage/*`. Every storage function takes `user_id` and filters by it — including lookups by id. Routers never build queries.
- Storage raises `NotFound` / `Invalid` / `Conflict`; `main.py` maps them to 404 / 422 / 409.
- Every schema change gets an Alembic migration (`render_as_batch` is on for SQLite). Keep `models.py` and migrations in sync.
- "Today" always comes from `app.timeutil.today()` (server TZ), never the browser clock. Dates in the API and frontend are `YYYY-MM-DD` strings.
- State-changing requests must send `X-Puffin: 1` (CSRF guard); `frontend/src/lib/api.ts` does this.
- Frontend: Svelte 5 runes, no extra runtime dependencies, plain CSS in `src/app.css` with CSS variables (light/dark). Mobile-first, big tap targets.
- Add tests for storage functions and any calculation (insights, streaks).

## Dev

No Python venv or Node is required on the host; Docker works for everything.

```bash
# Tests (in a container)
docker build --target test .

# Or locally, if you have python3-venv:
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest

# Backend dev server: reuse ../.env (APP_PASSWORD set, COOKIE_SECURE=false for http://localhost)
cd backend && mkdir -p ../data && set -a && . ../.env && set +a && export DATA_DIR=../data \
  && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload

# Frontend dev server (proxies /api to :8000)
cd frontend && npm install && npm run dev
#   without local Node:
docker run --rm -it -u $(id -u) -e npm_config_cache=/tmp/.npm -v $PWD/frontend:/app -w /app \
  --network host node:22-alpine sh -c "npm install && npm run dev"

# Type-check the frontend
cd frontend && npm run check

# New migration
cd backend && .venv/bin/alembic revision --autogenerate -m "describe change"
```

## Rebuild / run the container

```bash
docker compose build && docker compose up -d
docker compose logs -f
```

The container runs as `PUID:PGID` (default 1000) with a read-only root filesystem; only `/data` and `/tmp` are writable.
