"""
📋 LOGGING — Fayl va konsol loglash sozlamasi
"""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

FMT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Loglashni sozlash: konsol + rotating fayl."""
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(FMT, datefmt=DATE_FMT)

    # Konsol handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)

    # Fayl handler (5 MB, 3 ta zaxira fayl)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Telegram kutubxonasi loglarini kamroq ko'rsatish
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
