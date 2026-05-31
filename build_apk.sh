#!/usr/bin/env bash
# Build the nurse Android app pointed at this laptop's CURRENT LAN IP, then
# publish it so the phone can install it over WiFi (no USB cable) from:
#     http://<lan-ip>:8000/patient-care.apk
#
# Usage:
#   ./build_apk.sh            # auto-detect LAN IP
#   ./build_apk.sh 192.168.0.108   # force a specific IP
#   PORT=8000 ./build_apk.sh       # override backend port

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
export PATH="/opt/homebrew/bin:$PATH"   # Flutter / adb live here on this machine

PORT="${PORT:-8000}"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
blue()  { printf "\033[34m%s\033[0m\n" "$*"; }

# --- 1. Detect LAN IP (first arg overrides) ---
LAN_IP="${1:-$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)}"
if [ -z "${LAN_IP:-}" ]; then
  red "Could not detect a LAN IP — are you on WiFi? Pass one explicitly:"
  red "  ./build_apk.sh 192.168.0.108"
  exit 1
fi

# --- 2. Toolchain check ---
if ! command -v flutter >/dev/null 2>&1; then
  red "flutter not found on PATH. Install the Flutter SDK first."
  exit 1
fi

BACKEND_URL="http://$LAN_IP:$PORT"
blue "Building release APK pointed at $BACKEND_URL ..."

# --- 3. Build ---
cd "$ROOT/app_flutter"
flutter build apk --release --dart-define=BACKEND_URL="$BACKEND_URL"

APK="$ROOT/app_flutter/build/app/outputs/flutter-apk/app-release.apk"
if [ ! -f "$APK" ]; then
  red "Build finished but no APK was produced at:"
  red "  $APK"
  exit 1
fi

# --- 4. Publish for cable-free install (served by the backend's static dir) ---
mkdir -p "$ROOT/web/dist"
cp "$APK" "$ROOT/web/dist/patient-care.apk"
SIZE="$(du -h "$APK" | awk '{print $1}')"

# --- 5. Verify the backend is actually serving it ---
code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/patient-care.apk" 2>/dev/null || true)"

cat <<EOF

$(green "=== APK READY ($SIZE) ===")

Install on your phone (same WiFi as this laptop, no cable):
  1. Open in the phone's browser:
       $(green "$BACKEND_URL/patient-care.apk")
  2. Download -> tap the file -> allow "install unknown apps" -> Install.
  3. Sign in as a nurse and join a bed with its code.

For it to work, the backend must be running and reachable:
  cd "$ROOT/backend" && source .venv/bin/activate && \\
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
EOF

if [ "$code" = "200" ]; then
  green "Verified: the download URL is live right now."
else
  red "Heads up: the backend isn't serving the APK yet (got '${code:-no response})."
  red "Start it (command above) — it must have been launched AFTER web/dist existed."
fi

echo
blue "Re-run this script whenever your WiFi or IP changes (it re-detects automatically)."
