"""Patient Gateway — bridges Arduino serial ↔ cloud backend.

Replaces the old test.py Telegram bot. Two concurrent loops:

1. Serial reader: parses button presses → POSTs to /api/v1/gateway/events
2. WebSocket client: holds /ws/gateway open to receive MSG/REM/EMERGENCY/ACK
   commands from the backend, then writes them to the Arduino over serial
   (and optionally speaks them locally).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from urllib.parse import urlparse, urlunparse

import httpx
import serial
import websockets

from config import cfg
from speech import speak

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gateway")

KNOWN_BUTTONS = {"WATER", "MEDICINE", "HELP", "BATHROOM"}
_LOCAL_SPEECH = {
    "WATER": "Patient needs water",
    "MEDICINE": "Patient needs medicine",
    "HELP": "Emergency help needed",
    "BATHROOM": "Patient needs the bathroom",
}


def _ws_url() -> str:
    """Convert http(s)://host → ws(s)://host/ws/gateway?token=..."""
    parsed = urlparse(cfg.backend_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/ws/gateway", "", f"token={cfg.device_token}", ""))


async def report_event(client: httpx.AsyncClient, event_type: str) -> None:
    try:
        r = await client.post(
            "/api/v1/gateway/events",
            headers={"Authorization": f"Bearer {cfg.device_token}"},
            json={"type": event_type},
            timeout=10,
        )
        r.raise_for_status()
        log.info("reported %s → %s", event_type, r.json().get("id"))
    except httpx.HTTPError as e:
        log.error("failed to report %s: %s", event_type, e)


def _write_serial(ser: serial.Serial, raw: str) -> None:
    try:
        ser.write(raw.encode("utf-8"))
    except Exception as e:  # noqa: BLE001
        log.warning("serial write failed: %s", e)


async def serial_loop(ser: serial.Serial, client: httpx.AsyncClient) -> None:
    buffer = ""
    while True:
        try:
            if ser.in_waiting > 0:
                char = ser.read().decode("utf-8", errors="ignore")
                if char == "\n":
                    line = buffer.strip().upper()
                    buffer = ""
                    if not line:
                        continue
                    log.info("[serial] %s", line)
                    if line in KNOWN_BUTTONS:
                        speak(_LOCAL_SPEECH[line])
                        await report_event(client, line)
                    elif line == "SYSTEM_STARTED":
                        log.info("Arduino reports ready")
                else:
                    buffer += char
        except Exception as e:  # noqa: BLE001
            log.warning("serial read error: %s", e)
        await asyncio.sleep(0.05)


async def _handle_inbound(ser: serial.Serial, event: dict) -> None:
    kind = event.get("kind", "")
    if kind == "MSG":
        text = event.get("text", "")
        log.info("[backend → patient] MSG %r", text)
        _write_serial(ser, f"MSG:{text}\n")
        speak(text)
    elif kind == "REM":
        text = event.get("message", "")
        log.info("[backend → patient] REM %r", text)
        _write_serial(ser, f"REM:{text}\n")
        speak(text)
    elif kind == "EMERGENCY":
        log.warning("[backend → patient] EMERGENCY")
        _write_serial(ser, "EMERGENCY\n")
        speak("Emergency triggered")
    elif kind == "ACK":
        log.info("[backend → patient] ACK %s", event.get("alert_id"))
        _write_serial(ser, "ACK\n")
    else:
        log.info("[backend → patient] unknown event: %s", event)


async def ws_loop(ser: serial.Serial) -> None:
    """Connect to backend WS and process inbound commands. Reconnects forever."""
    while True:
        try:
            log.info("connecting WS to backend")
            async with websockets.connect(_ws_url(), ping_interval=20, ping_timeout=20) as ws:
                log.info("WS connected")
                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("bad WS payload: %r", raw)
                        continue
                    await _handle_inbound(ser, event)
        except Exception as e:  # noqa: BLE001
            log.warning("WS disconnected: %s — retrying in 3s", e)
            await asyncio.sleep(3)


async def main() -> int:
    if not cfg.device_token:
        log.error("DEVICE_TOKEN missing — pair this device via the backend first.")
        return 2
    log.info("opening serial %s @ %d", cfg.serial_port, cfg.baud)
    try:
        ser = serial.Serial(cfg.serial_port, cfg.baud, timeout=1)
    except serial.SerialException as e:
        log.error("could not open serial port: %s", e)
        return 3
    await asyncio.sleep(2)  # let Arduino reset settle
    log.info("backend: %s", cfg.backend_url)

    async with httpx.AsyncClient(base_url=cfg.backend_url) as client:
        try:
            r = await client.get("/health", timeout=5)
            r.raise_for_status()
            log.info("backend health OK")
        except httpx.HTTPError as e:
            log.warning("backend not reachable yet: %s — will retry on first event", e)

        await asyncio.gather(serial_loop(ser, client), ws_loop(ser))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        log.info("bye")
