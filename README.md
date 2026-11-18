# Puffin Journal

A self-hosted daily mood journal for people who are lazy about journaling.
The daily check-in takes under 30 seconds: tap your mood, energy and sleep,
tap a few tags, optionally answer one short prompt. Done.

Single Docker container, SQLite on a volume, no external services, no
trackers, no CDN calls. One user, behind a login.

## Features

**Now (Phase 1)**

- One-screen, mobile-first check-in: mood (big emoji), energy, sleep quality (optional)
- Tag chips (work, social, exercise, outside, family, rest, rough day…), most-used first, add new ones inline
- One rotating prompt per day ("One good thing today?") with quick-answer chips; skippable in one tap
- Optional free-text note. An entry with only taps is complete. One Save button.
- Backfill or edit any past day (arrows or date picker)
- History list with search and tag filter
- Settings: manage tags and the prompt pool
- Login with argon2-hashed password, rate-limited, signed session cookie

**Coming** — see [Roadmap](#roadmap).

## Quick start

```bash
git clone <your-repo-url> puffin-journal
cd puffin-journal
cp env.example .env
mkdir data
```

Edit `.env`: set `APP_PASSWORD` and `TZ`. Then:

```bash
docker compose up -d
```

Open `http://<host>:8000` and log in.

## Configuration

All settings live in `.env` (see `env.example` for comments). `.env` is gitignored.

| Variable | Default | Description |
|---|---|---|
| `APP_USERNAME` | `me` | Login username |
| `APP_PASSWORD` | — (required) | Login password, ≥8 characters. Hashed in memory at startup |
| `APP_PASSWORD_HASH` | — | Optional instead of `APP_PASSWORD`: argon2 hash from `python -m app.cli hash-password`, in single quotes. Wins if both are set |
| `SECRET_KEY` | auto | Signs session cookies. Leave empty to auto-generate into `./data/secret_key` |
| `TZ` | `UTC` | IANA timezone; decides what "today" is |
| `PORT` | `8000` | Host port |
| `COOKIE_SECURE` | `auto` | HTTPS-only session cookie. `auto` = when the request is HTTPS; `true` forces it (login then fails over plain HTTP); `false` never |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxy IPs trusted for `X-Forwarded-For` (login rate limit) |
| `LOG_ACCESS` | `false` | Log request paths (never bodies) |
| `PUID` / `PGID` | `1000` | uid/gid the container runs as; must own `./data` |
| `NTFY_URL` / `NTFY_TOPIC` | — | Reminders via ntfy (Phase 4, not used yet) |
| `REMINDER_TIME` | `20:30` | Reminder time, local (Phase 4, not used yet) |

The app refuses to start if no password is set, or if a value is still the
example placeholder. Changing the password or secret logs out every session.
`./data/secret_key` is part of your data: back it up with the database (if
it's lost, a new one is generated and you just log in again).

## Backup and restore

Everything is in `./data/journal.db` (SQLite, WAL mode).

**Backup** (safe while running):

```bash
docker compose exec app python -c "import sqlite3; s=sqlite3.connect('/data/journal.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d); d.close()"
```

Then copy `./data/backup.db` somewhere safe. Or stop the container and copy the
whole `./data` folder. (Automatic nightly backups are planned for Phase 6.)

**Restore**:

```bash
docker compose down
cp /path/to/backup.db data/journal.db && rm -f data/journal.db-wal data/journal.db-shm
docker compose up -d
```

## Updating

```bash
git pull
docker compose build
docker compose up -d
```

Database migrations run automatically on startup. Back up first.

## Reverse proxy

Terminate TLS at a reverse proxy and forward to the container. With Caddy:

```
journal.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

- In `docker-compose.yml`, publish on loopback only: `"127.0.0.1:${PORT:-8000}:8000"`.
- Set `FORWARDED_ALLOW_IPS` to the proxy's IP as seen by the container (for a
  proxy on the host that's usually the Docker bridge gateway, e.g. `172.17.0.1`;
  or `*` if nothing else can reach the port), so the login rate limit sees real
  client IPs.
- With `COOKIE_SECURE=auto` the cookie becomes HTTPS-only once the proxy is trusted; set `true` to enforce it.

## LAN-only / Tailscale

This holds personal data — it doesn't need to be on the public internet.

- **Tailscale**: bind the port to your tailnet IP (`"100.x.y.z:8000:8000"`), or
  use `tailscale serve --bg 8000` to get HTTPS on your `*.ts.net` name (`auto` handles
  the cookie either way).
- **LAN over plain HTTP**: works with the default `COOKIE_SECURE=auto`. Anyone on the network can
  see traffic, so prefer Tailscale or a proxy with TLS.
- Encryption at rest is left to the volume (e.g. LUKS / encrypted dataset).

## Development

See [CLAUDE.md](CLAUDE.md) for the layout and dev commands. Tests:

```bash
docker build --target test .
```

## Roadmap

See [PLAN.md](PLAN.md) for the full checklist.

- **Phase 2** — calendar heatmap, mood/energy trends (7/30/90 days), gentle streak counter
- **Phase 3** — insights: mood by tag, by weekday, vs. sleep
- **Phase 4** — daily reminder via ntfy (pluggable notifier, web push later)
- **Phase 5** — installable PWA with offline check-in and sync
- **Phase 6** — CSV/JSON export, JSON import, nightly backups (keep 14)

## Tech

FastAPI · SQLAlchemy 2 · Alembic · SQLite · Svelte 5 + Vite (no SvelteKit).
Svelte was chosen because it compiles to a small vanilla-JS bundle (~24 KB
gzipped) with no framework runtime, and reactive form state makes a tap-driven
form trivial. The SPA is a static build served by FastAPI, so there's no Node
at runtime.
