#!/usr/bin/env bash
# Rebuild + install the Android APK using the laptop's current LAN IP.
# Use this if the LAN IP changed since yesterday's build.
set -u
cd "$(dirname "$0")"

export PATH="/opt/homebrew/bin:$PATH"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
if [ -z "${LAN_IP:-}" ]; then
  echo "Could not detect LAN IP. Set it manually:  ./rebuild_app.sh <ip>"
  exit 1
fi
if [ -n "${1:-}" ]; then LAN_IP="$1"; fi
echo "Building APK pointed at http://$LAN_IP:8000 ..."
cd app_flutter
flutter build apk --debug --dart-define=BACKEND_URL=http://$LAN_IP:8000
DEV="$(adb devices | awk 'NR==2 {print $1}')"
if [ -z "$DEV" ]; then
  echo "No Android device detected. Plug your phone in (USB debugging on) and re-run."
  exit 2
fi
adb -s "$DEV" install -r build/app/outputs/flutter-apk/app-debug.apk
adb -s "$DEV" shell am force-stop com.patientcare.patient_care
adb -s "$DEV" shell am start -n com.patientcare.patient_care/.MainActivity
echo "Installed and launched on $DEV."
