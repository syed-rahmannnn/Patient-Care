# Demo runbook — start everything end-to-end

**Assumes:** the app is already installed on the phone, the patient device is plugged
into the laptop by USB, and the phone + laptop are on the **same WiFi**.

Project root (run commands from here unless noted):
`/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care`

---

## 0. Confirm the laptop IP still matches the app

The app has the laptop's IP baked in. Check it hasn't changed:

```bash
ipconfig getifaddr en0
```

- Prints **`192.168.0.108`** → good, continue.
- Prints something else → the IP changed since the APK was built. Rebuild + reinstall:
  ```bash
  cd "/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care"
  ./build_apk.sh
  ```
  Then on the phone reopen `http://<new-ip>:8000/patient-care.apk` and reinstall.

---

## 1. Start the stack — one command (recommended)

```bash
cd "/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care"
./start_demo.sh
```

Wait for `=== DEMO READY ===`. This brings up **Postgres + backend + gateway** in the
background. (If Docker isn't running yet, run `open -a Docker` first and wait ~15s.)

### …or start the three pieces manually (three terminals)

**Terminal 1 — database**
```bash
open -a Docker            # only if Docker Desktop isn't already running
docker start pcs-pg
```

**Terminal 2 — backend + website**
```bash
cd "/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care/backend"
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 3 — gateway (patient device bridge)**
```bash
cd "/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care/gateway"
source ../.venv/bin/activate
python gateway.py
```

---

## 2. Sanity checks (on the laptop)

```bash
curl -s http://localhost:8000/health     # -> {"status":"ok"}
ls /dev/cu.usbmodem*                      # the device's serial port should appear
```

- Gateway log should show `backend health OK` and `WS connected`.
  If started via `start_demo.sh`: `tail -f /tmp/pcs-gateway.log`
- If the serial port is **not** `/dev/cu.usbmodem1101`, set the correct one in
  `gateway/.env` → `SERIAL_PORT=...` and restart the gateway.

---

## 3. On the phone

1. Open the **Patient Care** app.
2. Sign in: **`nurse1@patient.care`** / **`Test1234!`**
3. **Allow** the notification permission prompt (needed for push).
4. You should already see **Room 101 · Bed 1** (nurse1 is pre-assigned).
   If not, tap **Join bed** and enter the code **`WR4-F69`**.

---

## 4. Test the round-trip

1. Press a button on the device (WATER / MEDICINE / HELP / BATHROOM).
2. Within ~1–2s the phone gets a **push notification** and the request appears
   **live** in the app — and on the admin website
   (`http://192.168.0.108:8000`, login `admin@patient.care` / `Test1234!`).
3. Tap **Acknowledge** in the app → the website updates live.

---

## 5. Stop everything

```bash
cd "/Users/syedrahman/Documents/My Projects/PDD Research/Patient-Care"
./stop_demo.sh                 # if you used start_demo.sh
# (manual mode: Ctrl+C each terminal, then `docker stop pcs-pg`)
```

---

## Troubleshooting

- **Phone login spins / "can't connect":** laptop IP changed (redo step 0) or the
  backend isn't running with `--host 0.0.0.0`. Confirm both devices are on the same WiFi.
- **In-app works but no push:** fully close and reopen the app once after login (that
  registers the push token), and make sure notifications are allowed for the app.
- **Gateway can't open serial:** check the USB cable, run `ls /dev/cu.usbmodem*`, and set
  `SERIAL_PORT` in `gateway/.env` to the listed port.
- **Live logs:** backend `tail -f /tmp/pcs-backend.log` · gateway `tail -f /tmp/pcs-gateway.log`
- **Reset demo data** (rooms/beds/nurses/sample requests): with Postgres up,
  `cd backend && source .venv/bin/activate && python seed.py`
