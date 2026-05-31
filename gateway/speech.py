import logging
import platform
import shutil
import subprocess

from config import cfg

logger = logging.getLogger(__name__)

_SYS = platform.system()


def speak(text: str) -> None:
    """Speak text out loud. macOS → `say`; Linux → `espeak` (if installed)."""
    if not text:
        return
    try:
        if _SYS == "Darwin":
            subprocess.run(["say", "-r", str(cfg.speech_rate), text], check=False)
            return
        if _SYS == "Linux" and shutil.which("espeak"):
            subprocess.run(["espeak", "-s", str(cfg.speech_rate), text], check=False)
            return
        logger.info("[speech disabled] %s", text)
    except Exception as e:  # noqa: BLE001 — speech is best-effort
        logger.warning("speech failed: %s", e)
