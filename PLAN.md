# Puffin Journal — Plan

Phased checklist. Tick items as they land and add notes for anything that
changed direction. The full original brief is in [SPEC.md](SPEC.md).

## Phase 1 — Core check-in ✅ (2026-11-17)

- [x] FastAPI backend, SQLAlchemy 2.0, SQLite on `/data`, Alembic migration `0001_initial`
- [x] Schema with `users` table and `user_id` on every data table; all storage functions scoped by user
- [x] Storage layer isolated in `backend/app/storage/` (only place that touches the DB)
- [x] Auth: plain `APP_PASSWORD` (hashed in memory) or argon2 `APP_PASSWORD_HASH`; `SECRET_KEY` auto-generated into `/data/secret_key` if unset; signed HttpOnly session cookie (30 days), per-IP login rate limit, CSRF header guard, sessions invalidated when the password or secret changes
- [x] Check-in screen: mood (emoji), energy, sleep (optional), tag chips (most-used first, inline add), daily rotating prompt with quick-answer chips and one-tap skip, optional note, single Save
- [x] Backfill / edit any past day (‹ › arrows, date picker; future dates rejected); delete an entry
- [x] History list: newest first, text search (note / prompt answer), multi-tag filter (AND), paging
- [x] Settings: add / rename / remove (archive if used) / restore tags; add / edit / toggle / delete prompts and quick answers; logout
- [x] "Today" computed in configured `TZ`
- [x] Security headers (strict CSP, no-store on API, frame deny); no third-party requests; access log off by default
- [x] Tests: storage layer, prompt rotation, timezone, auth/rate limit, API flows, startup config check, credential handling (48 tests)
- [x] Multi-stage Dockerfile (node build → venv → slim runtime), non-root, healthcheck, optional `test` target
- [x] docker-compose (read-only rootfs, cap_drop ALL, volume, env_file, restart, healthcheck, TZ)
- [x] README, CLAUDE.md, env.example, .gitignore, .dockerignore

## Phase 2 — Views

- [ ] Calendar heatmap coloured by mood (year / month view, tap a day to open it)
- [ ] Mood + energy trend line, 7 / 30 / 90 day ranges (hand-rolled SVG, no chart library)
- [ ] Gentle streak counter: count check-ins in the last N days / current run; missed days are never shown as failures (no red, no "streak lost")
- [ ] API: `GET /api/stats/calendar?from&to`, `GET /api/stats/trend?days=`

## Phase 3 — Insights

- [ ] Average mood by tag (with entry counts; hide tags with < 3 uses)
- [ ] Average mood by weekday
- [ ] Mood vs. sleep quality
- [ ] Pure functions in `backend/app/insights.py` fed by a storage query, with unit tests for each calculation (empty data, single entry, ties, missing sleep)

## Phase 4 — Reminders

- [ ] `Notifier` protocol (`async send(title, body)`) in `backend/app/notify/`; `NtfyNotifier` using `NTFY_URL` / `NTFY_TOPIC` (stdlib or httpx, no SDK)
- [ ] In-process scheduler (asyncio task started in lifespan) firing at `REMINDER_TIME` in `TZ`; skip if today already has an entry
- [ ] Settings toggle + "send test notification" button
- [ ] Design so a `WebPushNotifier` can be added later (VAPID keys in env)
- [ ] Note: ntfy is the only outbound call allowed; the message must not contain entry content

## Phase 5 — PWA / offline

- [ ] `manifest.webmanifest`, PNG + maskable icons, installable
- [ ] Service worker: precache app shell, network-first for `/api`, offline fallback
- [ ] Offline check-in: queue PUTs in IndexedDB, replay on reconnect (last-write-wins per date, idempotent PUT already supports this)
- [ ] Cache today's prompt + tags for offline use
- [ ] "Pending sync" indicator
- [ ] Revisit CSP for the service worker (`worker-src 'self'`)

## Phase 6 — Data export, import, backups

- [ ] Export CSV and JSON from settings (`GET /api/export.csv`, `/api/export.json`)
- [ ] Import from the JSON export (validate, dry-run summary, upsert by date, map tags/prompts by name)
- [ ] Nightly backup of the DB into `/data/backups/journal-YYYY-MM-DD.db` using SQLite's online backup API; keep the last 14
- [ ] Tests for export → import round trip and backup rotation

## Design notes for later (not scheduled)

- **Multi-user**: schema and storage are already user-scoped. Would need a users UI, password hashes in DB instead of env, and per-user settings.
- **Encryption**: currently relies on volume encryption + TLS at the proxy. App-level field encryption (note, prompt_answer) would go entirely inside `app/storage/` (encrypt on write, decrypt on read); search would then need a different approach.
- **Sessions**: stateless signed cookies. A server-side sessions table would allow "log out everywhere" without rotating `SECRET_KEY`.
- **Rate limiter** is in-memory per process; fine for one worker. Move to SQLite if running multiple workers.
