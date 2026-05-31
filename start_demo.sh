#!/usr/bin/env bash
# Demo bring-up script. Starts Postgres + backend + gateway.
# Run from the project root:  ./start_demo.sh

set -u
cd "$(dirname "$0")"
ROOT="$(pwd)"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
blue()  { printf "\033[34m%s\033[0m\n" "$*"; }

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo unknown)"
blue "Laptop LAN IP: $LAN_IP"

# --- Postgres ---
if ! docker ps --format '{{.Names}}' | grep -q '^pcs-pg$'; then
  if docker ps -a --format '{{.Names}}' | grep -q '^pcs-pg$'; then
    blue "Starting existing pcs-pg container..."
    docker start pcs-pg >/dev/null
  else
    blue "Creating pcs-pg container..."
    docker run --name pcs-pg -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_DB=patient_care -p 5432:5432 -d postgres:16 >/dev/null
  fi
fi
for i in 1 2 3 4 5; do
  if docker exec pcs-pg pg_isready -U postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
green "Postgres ready on :5432"

# --- Backend ---
pkill -9 -f 'uvicorn app.main:app' 2>/dev/null || true
sleep 1
(
  cd "$ROOT/backend"
  source .venv/bin/activate
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
    > /tmp/pcs-backend.log 2>&1 &
  disown
)
for i in 1 2 3 4 5 6 7 8; do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 1
done
if curl -s http://localhost:8000/health | grep -q '"ok"'; then
  green "Backend ready on http://$LAN_IP:8000"
else
  red "Backend did not start. See /tmp/pcs-backend.log"
fi

# --- Gateway ---
pkill -9 -f 'gateway.py' 2>/dev/null || true
sleep 1
if ! ls /dev/cu.usbmodem* 2>/dev/null | head -1 >/dev/null; then
  red "WARN: No /dev/cu.usbmodem* device found. Plug the Arduino in."
fi
(
  cd "$ROOT/gateway"
  source ../.venv/bin/activate
  nohup python gateway.py > /tmp/pcs-gateway.log 2>&1 &
  disown
)
sleep 3
if pgrep -f 'gateway.py' >/dev/null; then
  green "Gateway running (PID $(pgrep -f 'gateway.py' | head -1))"
else
  red "Gateway failed to start. See /tmp/pcs-gateway.log"
fi

cat <<EOF

$(green "=== DEMO READY ===")

Admin website (open in a browser):
  http://localhost:8000        (or http://$LAN_IP:8000 from another device)
  Email:    admin@patient.care
  Password: Test1234!

Login on the phone (nurse app):
  Email:    nurse1@patient.care
  Password: Test1234!
  Join a bed with the code shown on the website (Rooms & Beds → a bed).

Tail logs in another terminal:
  tail -f /tmp/pcs-backend.log
  tail -f /tmp/pcs-gateway.log

Stop everything:
  ./stop_demo.sh

If the phone can't reach the backend, your laptop's LAN IP may have changed.
Current IP: $LAN_IP
The APK was built against http://192.168.0.101:8000. If $LAN_IP differs, run:
  ./rebuild_app.sh

EOF
