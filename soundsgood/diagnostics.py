# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Local diagnostics and exception reporting for SoundsGood."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import sys
import threading


LOGGER_NAME = "soundsgood"
_configured = False


def diagnostics_dir() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "soundsgood"


def diagnostics_file() -> Path:
    return diagnostics_dir() / "soundsgood.log"


def configure_logging(version: str = "unknown") -> logging.Logger:
    """Configure a bounded local log and process-wide exception hooks."""
    global _configured

    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(threadName)s] %(message)s"
    )

    try:
        directory = diagnostics_dir()
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            diagnostics_file(),
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except OSError:
        # A read-only or unavailable state directory must not prevent startup.
        pass

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    previous_excepthook = sys.excepthook

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            previous_excepthook(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception

    if hasattr(threading, "excepthook"):
        def handle_thread_exception(args):
            logger.error(
                "Unhandled worker exception",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = handle_thread_exception

    _configured = True
    logger.info(
        "Starting SoundsGood version=%s python=%s platform=%s",
        version,
        platform.python_version(),
        platform.platform(),
    )
    return logger


def get_logger(component: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
