# Patient Gateway

USB-tethered bridge between the patient device (Arduino + TFT + buttons)
and the cloud backend. Successor to the original `test.py` Telegram bot.

This script runs on whatever computer is plugged into the Arduino — your Mac
for development, or a Raspberry Pi for deployment.

## Setup

```bash
cd gateway

# Use the project-root venv (Python 3.14 is fine here — no pydantic needed)
source ../.venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# fill in:
#   DEVICE_TOKEN  — from POST /api/v1/rooms/{room_id}/devices on the backend
#   SERIAL_PORT   — `ls /dev/tty.usb*` (macOS) or `/dev/ttyUSB0` / `/dev/ttyACM0` (Linux)

python gateway.py
```

## Verifying M2

1. Backend running (`cd backend && uvicorn app.main:app --reload`).
2. Log in as admin → create room → pair device → copy the `token` returned.
3. Paste that token into `gateway/.env` as `DEVICE_TOKEN`.
4. `python gateway.py` — should print `Arduino reports ready` once the
   Arduino sends `SYSTEM_STARTED`.
5. Press the WATER button on the Arduino — gateway logs `reported WATER → <uuid>`.
6. `GET /api/v1/rooms/{room_id}/alerts` returns the new alert.
7. If `FIREBASE_CREDS_JSON` is set in the backend, registered FCM tokens get the push.

## Linux deployment notes

- Install `espeak` for local voice feedback: `sudo apt install espeak`.
- Add the user to `dialout` group so the serial port is readable:
  `sudo usermod -a -G dialout $USER` (then re-login).
- Run as a systemd service for auto-start on boot (sample unit not yet shipped).
