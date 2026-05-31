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

# Event delivery retry/queue — so a button tap during a backend blip isn't lost.
# Taps are enqueued (never blocking the serial reader) and a background worker
# POSTs them, retrying with exponential backoff until the backend comes back.
EVENT_QUEUE_MAX = 200       # plenty for human-paced taps; drops oldest-style log if full
RETRY_BASE_DELAY = 1.0      # first retry after 1s
RETRY_MAX_DELAY = 15.0      # cap backoff at 15s
RETRY_MAX_ATTEMPTS = 20     # ~a few minutes of outage tolerance per event before giving up
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


def enqueue_event(queue: "asyncio.Queue[str]", event_type: str) -> None:
    """Hand a button event to the reporter worker. Never blocks the serial loop."""
    try:
        queue.put_nowait(event_type)
        if queue.qsize() > 1:
            log.info("queued %s (%d pending delivery)", event_type, queue.qsize())
    except asyncio.QueueFull:
        log.error("event queue full (%d) — dropping %s", EVENT_QUEUE_MAX, event_type)


async def reporter_loop(client: httpx.AsyncClient, queue: "asyncio.Queue[str]") -> None:
    """Drain queued events to the backend, retrying with backoff until delivered.

    Runs as its own task so a backend outage never stalls the serial reader: taps
    keep getting queued here and flush in order the moment the backend recovers.
    """
    while True:
        event_type = await queue.get()
        delay = RETRY_BASE_DELAY
        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                r = await client.post(
                    "/api/v1/gateway/events",
                    headers={"Authorization": f"Bearer {cfg.device_token}"},
                    json={"type": event_type},
                    timeout=10,
                )
                r.raise_for_status()
                log.info("reported %s → %s (attempt %d)", event_type, r.json().get("id"), attempt)
                break
            except httpx.HTTPError as e:
                if attempt >= RETRY_MAX_ATTEMPTS:
                    log.error("giving up on %s after %d attempts: %s", event_type, attempt, e)
                    break
                log.warning(
                    "report %s failed (attempt %d/%d): %s — retrying in %.0fs",
                    event_type, attempt, RETRY_MAX_ATTEMPTS, e, delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RETRY_MAX_DELAY)
        queue.task_done()


def _write_serial(ser: serial.Serial, raw: str) -> None:
    try:
        ser.write(raw.encode("utf-8"))
    except Exception as e:  # noqa: BLE001
        log.warning("serial write failed: %s", e)


async def serial_loop(ser: serial.Serial, queue: "asyncio.Queue[str]") -> None:
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
                        enqueue_event(queue, line)
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

        queue: "asyncio.Queue[str]" = asyncio.Queue(maxsize=EVENT_QUEUE_MAX)
        await asyncio.gather(
            serial_loop(ser, queue),
            reporter_loop(client, queue),
            ws_loop(ser),
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        log.info("bye")
