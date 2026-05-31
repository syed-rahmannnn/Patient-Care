import glob
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _resolve_serial_port(configured: str) -> str:
    """If the configured port is missing, auto-pick the first usbmodem* the OS sees.

    macOS sometimes reassigns the suffix after an unplug/replug (e.g.
    usbmodem101 → usbmodem1101). Falling back to a glob keeps the gateway
    working across replugs without manually editing .env.
    """
    if configured and os.path.exists(configured):
        return configured
    candidates = sorted(
        glob.glob("/dev/cu.usbmodem*")
        + glob.glob("/dev/tty.usbmodem*")
        + glob.glob("/dev/ttyUSB*")
        + glob.glob("/dev/ttyACM*")
    )
    if candidates:
        return candidates[0]
    return configured  # let serial.Serial() surface the real error


@dataclass(frozen=True)
class Config:
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    device_token: str = os.getenv("DEVICE_TOKEN", "")
    serial_port: str = _resolve_serial_port(os.getenv("SERIAL_PORT", ""))
    baud: int = int(os.getenv("BAUD", "9600"))
    speech_rate: int = int(os.getenv("SPEECH_RATE", "155"))


cfg = Config()
