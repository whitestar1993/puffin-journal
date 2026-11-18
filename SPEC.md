# Original brief

The brief this project was started from (2026-11-17). Progress is tracked in
[PLAN.md](PLAN.md); where they differ, PLAN.md records the decision.

---

Build a self-hosted daily mood journal as a PWA, deployed as a single Docker container. I'm lazy about journaling, so the whole design goal is: a daily check-in that takes under 30 seconds, mostly taps, with optional typing.

## Core features

**Daily check-in (one screen, mobile-first)**
- Mood: 1-5, big emoji buttons
- Energy: 1-5, tap
- Sleep quality: 1-5, tap (optional)
- Tag chips for what the day involved (defaults: work, social, exercise, outside, family, rest, rough day). I can add/remove/rename tags in settings. Most-used tags sort first.
- One rotating prompt per day from a configurable pool (e.g. "One good thing today?", "What drained you?", "What are you looking forward to?"). Always skippable in one tap. Answer by typing, or by tapping quick-answer chips. Prompt pool editable in settings.
- Optional free-text note.
- An entry with only taps counts as complete. Saving is one button.
- Easy to backfill or edit yesterday and past days.

**Views**
- Calendar heatmap colored by mood
- Mood/energy trend line (7/30/90 days)
- Simple insights: average mood by tag, by weekday, and vs. sleep quality
- History list with search and tag filter
- Streak counter that is gentle: missed days never show as failures

**Reminders**
- Daily reminder at a configurable time via ntfy (server URL and topic set in env). Make the notifier pluggable so web push could be added later.

**Data**
- SQLite on a mounted volume (/data)
- Export to CSV and JSON from settings; import from the JSON export
- Nightly automatic backup of the DB file into /data/backups, keep the last 14

## Tech and constraints
- Backend: Python FastAPI. Frontend: lightweight (Svelte or plain TS with Vite; no heavy frameworks). Choose and briefly justify.
- PWA: installable, manifest, service worker, works offline for the check-in and syncs when back online
- Single-user app protected by a login. Password set via env (hashed), session cookie, rate-limited login. No signup flow.
- No external services, trackers, analytics or CDN calls; everything is self-contained.
- Multi-stage Dockerfile, non-root user, healthcheck endpoint.
- Timezone configurable via env (TZ), since "today" must be correct.
- Add tests for the data layer and the insights calculations.

## Deliverables
1. `Dockerfile` and `docker-compose.yml` (volume for /data, port mapping, env_file, restart policy, healthcheck, TZ). Include a comment on running behind a reverse proxy.
2. `.env.example` with every variable documented (password, secret key, TZ, ntfy URL/topic, reminder time, port).
3. `README.md`: what it is, features, quick start (clone, copy .env, `docker compose up -d`), configuration table, backup/restore, updating, reverse proxy and Tailscale/LAN-only notes, and a short roadmap.
4. `CLAUDE.md` for future sessions: project overview, architecture and folder structure, how to run dev and tests, how to rebuild the container, coding conventions, the data model, and a note that this app holds sensitive personal data, so never add third-party calls or logging of entry content.
5. `.gitignore` and `.dockerignore`.

## Process
- Start with a short plan (architecture, data model, screen list) and wait for OK only if something is ambiguous; otherwise proceed.
- Build in stages: data model and API, then frontend, then PWA/offline, then reminders and backups, then Docker and docs.
- Run the tests and do a `docker compose build` and `up` smoke test before finishing, and fix anything that fails.
- Finish with a summary of what's built, how to start it, and any decisions that may want changing.

## Phase 1 scope only
Build only: auth, check-in screen (mood/energy/sleep/tags/prompt/note), edit past days, history list, Docker setup, and docs. Everything else goes in PLAN.md as later phases (heatmap and trends, insights, ntfy reminders, PWA offline, export/import, nightly backups).

## Design for later, don't build now
- Schema has a `users` table and a `user_id` on every data table; all queries scoped to the logged-in user. Single user for now, no signup UI.
- Use Alembic migrations from the start.
- Keep the API cleanly separated from the frontend.
- Encryption: assume volume-level encryption and TLS at the proxy; no app-level field encryption. Keep the storage layer isolated in one module so that could be added later.

## PLAN.md
Create PLAN.md with a phased checklist and keep it updated as work completes. In CLAUDE.md, instruct future sessions to read PLAN.md first and update it when finishing work.
