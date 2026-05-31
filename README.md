# Patient Care System

Real-time patient-to-caregiver notification platform. Successor to the
single-machine Telegram bot in `test.py`.

> Original project: SMD Abdur Rahman Ghouse — *Intelligent Patient Care and
> Vital Monitoring System with Real-Time Caregiver Alerts and Automated
> Medication Management* (Star Summit 2026).

## Components

```
Patient call device (TFT + buttons)
       │ USB serial
       ▼
gateway/                  Python bridge (replaces test.py) — serial ↔ cloud
       │ HTTPS REST + WebSocket
       ▼
backend/                  FastAPI + Postgres + FCM (Render free tier)
       ├── serves ──▶ web/         React admin dashboard (rooms · beds · nurses)
       │ FCM push + WebSocket
       ▼
app_flutter/              Flutter Android app for nurses
```

**Hierarchy:** `Room` (e.g. Room 101) → `Bed` (Bed 1, Bed 2 …). Each **bed** owns a unique
join code and (optionally) one connected device. An admin builds this on the website; a
nurse joins a bed by its code in the app, and a bed's requests route only to that bed's
nurses. A bed shows **Active** once a device is paired, **Inactive** otherwise.

Full design and rationale: `/Users/syedrahman/.claude/plans/read-this-code-silly-bachman.md`.

## Quickstart (local demo)

1. **Postgres** — `docker run --name pcs-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=patient_care -p 5432:5432 -d postgres:16`.
2. **Backend** —
   ```bash
   cd backend
   source .venv/bin/activate           # Python 3.13 venv
   cp .env.example .env                # FIREBASE_CREDS_JSON can stay empty initially
   python seed.py                      # admin + nurses + demo rooms/beds/device (prints bed codes + a device token)
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Admin login: `admin@patient.care` / `Test1234!`. API docs at <http://localhost:8000/docs>.
3. **Admin website** (`web/`) —
   ```bash
   cd web
   npm install
   npm run dev          # dev server at http://localhost:5173 (proxies /api + /ws to :8000)
   # — or — build once and let the backend serve it at http://localhost:8000 :
   npm run build
   ```
   Sign in as the admin, then go to **Rooms & Beds** to create rooms/beds, pair devices,
   and copy a bed's **join code** (and a device token when pairing).
4. **Gateway** —
   ```bash
   cd gateway
   source ../.venv/bin/activate        # the existing Python 3.14 venv is fine here
   pip install -r requirements.txt
   cp .env.example .env                # paste a bed's device token, set SERIAL_PORT
   python gateway.py
   ```
   Press a button on the device — the request appears live in the website and in
   `GET /api/v1/beds/{id}/alerts`, and is pushed to that bed's nurses.
5. **Flutter app** — see `app_flutter/README.md` (requires Flutter SDK). A nurse signs in,
   taps **Join bed**, and enters a bed's join code.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI service: auth, rooms, beds, devices, nurses, alerts, reminders, messages, dashboard, WebSocket hub, FCM fan-out, reminder poller. Also serves the built `web/` app. |
| `backend/seed.py` | Idempotent demo seeder — admin, nurses, rooms, beds, a paired device, sample requests |
| `web/` | React + Vite + Tailwind admin dashboard (TypeScript) |
| `gateway/` | Python USB-serial bridge (formerly `test.py`); REST client + WS client |
| `app_flutter/` | Flutter Android nurse app — Dart code complete, needs `flutter create` to scaffold platform files |
| `test.py` | **Legacy** Telegram bot — kept for reference; superseded by `gateway/` |
| `handoff.md` | Star Summit poster notes (unrelated to the app build) |

## Status of each milestone

- ✅ **M1** Backend skeleton + auth (JWT, Postgres, Alembic-ready).
- ✅ **M2** Button flow end-to-end: gateway → backend → FCM fan-out.
- ✅ **M3** Persistent reminders (asyncio poller, 15 s tick), alert ack, room WebSocket.
- ✅ **M4** Nurse → patient messages + dedicated emergency channel; gateway holds WS for inbound commands.
- 🟡 **M5** Flutter app — Dart source code written and `pubspec.yaml` ready. User must install the Flutter SDK and run `flutter create` to generate the Android platform scaffold (see `app_flutter/README.md`).

## Deploying the backend to Render

1. Push the repo to GitHub.
2. In Render: "New → Blueprint" → point at `backend/render.yaml`.
3. Render creates a `patient-care-api` web service + `patient-care-db` Postgres.
4. Set the secret env vars (in Dashboard → Environment):
   - `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`
   - `FIREBASE_CREDS_JSON` — paste the entire service-account JSON as a single line.
5. Add an UptimeRobot HTTP monitor on `https://patient-care-api.onrender.com/health`
   every 10 minutes to prevent the free tier from sleeping.

## Known gotchas (kept from the plan's research phase)

- **Python 3.14** is too new for `pydantic-core` wheels — the backend uses a
  dedicated `.venv` on Python 3.13. The gateway can run on either.
- **Render free tier** sleeps after 15 min idle; first request after sleep
  cold-starts in ~30 s. UptimeRobot ping (see above) mitigates this.
- **FCM tokens** rotate; the backend purges stale tokens on `UNREGISTERED`
  responses automatically.
- **WebSocket auth** uses a short-lived (60 s) JWT obtained from
  `POST /api/v1/auth/ws-ticket` immediately before opening the socket.
