# Patient Care — Deployment Runbook

Split deployment:

```
[ Raspberry Pi (this machine) ]                 [ Your Dokploy server ]
  Arduino ──USB serial──► gateway.py              Traefik (HTTPS + WSS, Let's Encrypt)
                             │                              │
                             └─ HTTPS REST + WSS ───────────► backend (FastAPI) + Postgres
                                to ptcare.welocalhost.com      └─ also serves the admin website
```

- **Dokploy server** runs the **backend + Postgres + admin website** as one Compose stack,
  published at `https://ptcare.welocalhost.com`.
- **Raspberry Pi** runs the **gateway only** — it dials *out* to that URL over REST + WebSocket.
  No backend, no Docker, no Postgres on the Pi.

There is **no Cloudflare Tunnel** in this setup — Dokploy's built-in Traefik already terminates
HTTPS/WSS for the subdomain you pointed at the server.

---

## ✅ Already done on this Raspberry Pi (gateway side)

- Created `gateway/.venv` (Python 3.13.5) and installed `gateway/requirements.txt`
  (pyserial, httpx, websockets, python-dotenv).
- Installed `espeak` (optional local voice).
- Wrote `gateway/.env`:
  - `BACKEND_URL=https://ptcare.welocalhost.com`
  - `SERIAL_PORT=/dev/ttyACM0`  (Arduino is plugged in; `pi` is already in the `dialout` group)
  - `DEVICE_TOKEN=`  ← **blank until you pair a bed (Phase 6)**
- Installed the systemd unit `/etc/systemd/system/patient-care-gateway.service`
  (from `gateway/patient-care-gateway.service`). It is **installed but NOT enabled** — the
  gateway exits immediately while `DEVICE_TOKEN` is blank, so we start it after pairing.

Verified: config loads, all imports work, and the WS URL builds as
`wss://ptcare.welocalhost.com/ws/gateway?token=…`.

---

## ✅ Already authored (repo files for the Dokploy deploy)

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | The Compose stack Dokploy deploys: `backend` + `postgres`. |
| `Dockerfile` (repo root) | Multi-stage: builds the React admin site (`web/`) and bakes it into the backend image at `/web/dist`, so FastAPI serves `/api`, `/ws`, **and** the admin site from one origin. |
| `.dockerignore` | Keeps the build context small. |
| `.env.example` | Template of the env vars (you set these in the Dokploy UI, not a file). |

> The existing `backend/Dockerfile` (single-stage, for Render) is left untouched. Dokploy uses
> the new **root** `Dockerfile` via `docker-compose.yml`.

---

## Phase 1 — Deploy backend + Postgres to Dokploy

### 1a. Get the source to a Git repo Dokploy can pull
Dokploy builds the multi-stage `Dockerfile` on the server, so it needs the **whole repo**
(the new `docker-compose.yml`, `Dockerfile`, `web/`, `backend/`). Commit and push these new
files to your Git remote (GitHub/GitLab/Gitea), e.g.:

```bash
cd /home/pi/Downloads/Patient-Care-main
git init                 # if not already a repo
git add .                # .gitignore already excludes .env, google-services.json, keys
git commit -m "Add Dokploy compose stack + gateway service"
git remote add origin <your-repo-url>
git push -u origin main
```
`.env` and other secrets are git-ignored — confirm `git status` does **not** list `.env`,
`gateway/.env`, or any `serviceAccount*.json` before pushing.

### 1b. Create the Compose application in Dokploy
1. Dokploy → your project → **Create Service → Compose**.
2. **Source: Git** → repo URL + branch (e.g. `main`).
3. **Compose Path:** `./docker-compose.yml`.

### 1c. Set environment variables (Dokploy → the service → Environment)
Required (the compose fails fast if these are unset):

| Variable | Value |
| --- | --- |
| `POSTGRES_PASSWORD` | a strong DB password (use the same one everywhere) |
| `JWT_SECRET` | long random — `openssl rand -hex 32` |
| `BOOTSTRAP_ADMIN_PASSWORD` | your admin login password |

Optional (sensible defaults in the compose):

| Variable | Default | Notes |
| --- | --- | --- |
| `POSTGRES_DB` | `patient_care` | |
| `BOOTSTRAP_ADMIN_EMAIL` | `admin@patient.care` | your admin login email |
| `DATABASE_URL` | auto-composed from the two POSTGRES vars | leave unset unless you need a custom DSN; if set, it **must** use `postgresql+asyncpg://…@postgres:5432/…` |
| `FIREBASE_CREDS_JSON` | empty (push disabled) | paste the service-account JSON **on one line** to enable nurse push — see Phase 4 |

> The admin user and all tables are created automatically on first startup
> (`backend/app/main.py:54-56` + `_bootstrap_admin`).

### 1d. Add the domain + HTTPS (this replaces "Phase 2")
In Dokploy → the service → **Domains → Add Domain**:
- **Host:** `ptcare.welocalhost.com`
- **Service:** `backend`  •  **Container Port:** `8000`  •  **Path:** `/`
- **HTTPS:** on  •  **Certificate:** Let's Encrypt

Prerequisites:
- DNS `ptcare.welocalhost.com` → your Dokploy server's public IP (you've done this).
- Ports **80 and 443 open** on the Dokploy server (Let's Encrypt ACME + serving).
- A Let's Encrypt email set in Dokploy server settings.
- WebSockets need no extra config — Traefik proxies `wss://…/ws/…` by default.

> **If the domain 404s/502s after deploy**, the `backend` service isn't on Dokploy's proxy
> network. Dokploy usually wires this automatically for Compose domains; if not, add to
> `docker-compose.yml` (Dokploy-only — this breaks a plain local `docker compose up`):
> ```yaml
>   backend:
>     networks: [default, dokploy-network]
> networks:
>   dokploy-network:
>     external: true
> ```

### 1e. Deploy & verify
Click **Deploy**. First build compiles the web app + installs Python deps (a few minutes).
Then verify (from anywhere, incl. the Pi):

```bash
curl -fsS https://ptcare.welocalhost.com/health      # -> {"status":"ok"}
```
Open `https://ptcare.welocalhost.com` → the admin dashboard should load; log in with
`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`.

> **Run exactly one backend replica.** The WebSocket hub is in-memory
> (`backend/app/ws_manager.py:21`), so a second replica would split the live feed and gateway
> return-commands. Don't scale the `backend` service. (Push/FCM would still work; only WS splits.)

---

## Phase 3 — Gateway on the Pi  (mostly done — finished in Phase 6)

Everything is installed (see "Already done" above). The gateway is **started in Phase 6**, right
after you pair a bed and obtain the device token. To dry-run it manually before enabling the
service (optional), once you have a token in `gateway/.env`:

```bash
/home/pi/Downloads/Patient-Care-main/gateway/.venv/bin/python \
  /home/pi/Downloads/Patient-Care-main/gateway/gateway.py
```

The Arduino sketch only has to print `WATER` / `MEDICINE` / `HELP` / `BATHROOM`
(newline-terminated) over serial on a button tap — that's the contract `gateway.py:29` expects.

---

## Phase 4 — Firebase

> **Setting up FCM from scratch? Follow `FIREBASE_SETUP.md`** — full step-by-step for creating the
> project and producing both files. Summary below.

**Backend (push fan-out):** paste your service-account JSON into `FIREBASE_CREDS_JSON` in Dokploy,
**on a single line**. Easiest:
```bash
jq -c . serviceAccount.json     # copy the one-line output, paste into Dokploy, redeploy
```
`backend/app/fcm.py:19` initializes Firebase lazily on the first push; until the var is set, the
app runs fine and just logs "FCM not configured".

**⚠️ App side is NOT ready — `app_flutter/android/app/google-services.json` is MISSING.**
The Android build applies the `com.google.gms.google-services` plugin
(`app_flutter/android/app/build.gradle.kts:6`), so **`flutter build apk` will fail without it.**
Fix before Phase 5:
1. Firebase console → your project → add/open the **Android app** with package
   **`com.patientcare.patient_care`** (must match `applicationId`).
2. Download its `google-services.json`.
3. Place it at `app_flutter/android/app/google-services.json` (git-ignored — don't commit).

---

## Phase 5 — Build the Flutter nurse app (on a machine with the Flutter SDK)

Flutter is **not** installed on this Pi, and `google-services.json` must be added first (Phase 4).
On your dev machine:

```bash
cd app_flutter
flutter pub get
flutter build apk --release --dart-define=BACKEND_URL=https://ptcare.welocalhost.com
# APK: build/app/outputs/flutter-apk/app-release.apk
```
- The compile-time `BACKEND_URL` is the default; the app also has an **in-app server-URL override**
  (`app_flutter/lib/api/client.dart:62`), so you can repoint it without rebuilding.
- Install on the nurse phone, sign in → the FCM token auto-registers via
  `POST /api/v1/me/fcm-tokens` (`app_flutter/lib/fcm/fcm_setup.dart:64`).
- (`build_apk.sh` in the repo root is **macOS-only / LAN-IP** oriented — use the command above for
  this public-URL build.)

---

## Phase 6 — Pair the device + end-to-end test

1. **Admin site** `https://ptcare.welocalhost.com` → **Rooms & Beds**:
   create a Room → create **Bed 1** → **Pair device** → copy the **device token**.
2. On the **Pi**, put that token into `gateway/.env` (`DEVICE_TOKEN=…`), then start the service:
   ```bash
   # edit DEVICE_TOKEN=... in /home/pi/Downloads/Patient-Care-main/gateway/.env
   sudo systemctl enable --now patient-care-gateway
   journalctl -u patient-care-gateway -f      # expect: "backend health OK" then "WS connected"
   ```
   The bed flips to **Active** in the admin site once the gateway's WS connects.
3. Copy **Bed 1's join code** from the admin site.
4. **Nurse app** → **Join bed** → enter Bed 1's join code.
5. Tap **Water** on the Arduino → expect **both**: an **FCM push** on the nurse phone **and** the
   in-app **live feed** updates over WebSocket (wired in `backend/app/routes/gateway.py:50-75`).

---

## Risks / ops notes

- **Single backend replica only** (in-memory WS hub) — see Phase 1e.
- **Gateway is host + systemd, not Docker** — USB-serial passthrough into containers is fragile;
  the host service has built-in serial + WS reconnect loops (`gateway/gateway.py:113-129`).
- **Postgres data** lives in the named volume `pgdata` — it survives redeploys. Set up a backup
  (`docker compose exec postgres pg_dump …` or Dokploy's backup feature) before going live.
- **Arch:** Dokploy builds on your server, so base images resolve to that server's architecture
  automatically. (`python:3.12-slim`, `node:20`, `postgres:16` are all multi-arch.)
- **Secrets:** `.env`, `gateway/.env`, `google-services.json`, and `serviceAccount*.json` are all
  git-ignored — keep them out of the repo. Rotate `JWT_SECRET`/DB password if they ever leak.
- **LAN exposure during testing:** the compose uses `expose` (not host `ports`), so the API is only
  reachable via the Traefik domain — nothing extra is opened on the Dokploy host.
