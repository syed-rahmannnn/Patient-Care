# Patient Care — Backend

FastAPI + Postgres backend for the Patient Care notification system.
Plan: `/Users/syedrahman/.claude/plans/read-this-code-silly-bachman.md`.

## Local setup

> Use **Python 3.13** — `pydantic-core` does not yet have Python 3.14 wheels (PyO3 cap).
> A dedicated `backend/.venv` is already created; the top-level `../.venv` remains on 3.14 for the gateway/old `test.py`.

```bash
cd backend

source .venv/bin/activate          # backend-local venv (Python 3.13)

pip install -r requirements.txt    # already done during initial scaffold

cp .env.example .env
# edit .env: set DATABASE_URL to a running Postgres, set a real JWT_SECRET

# need Postgres. quick option with Docker:
# docker run --name pcs-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=patient_care -p 5432:5432 -d postgres:16

uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> — interactive Swagger.

## Verifying M1

1. `GET /api/v1/auth/has-admin` → `{"has_admin": true}` (bootstrap admin is created on first start).
2. `POST /api/v1/auth/login` with `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` → token pair.
3. Click "Authorize" in Swagger, paste the access token.
4. `POST /api/v1/auth/register` to create a nurse.
5. `POST /api/v1/rooms` to create a room — note the `invite_code`.
6. `POST /api/v1/rooms/{id}/devices` with a `serial_id` like `PCS-001` → returns a long-lived **device token** for the gateway.
7. Log in as the nurse, `POST /api/v1/rooms/join` with the invite code.
8. `POST /api/v1/me/fcm-tokens` to register a fake FCM token.
