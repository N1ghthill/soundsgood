# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import json
import os
from pathlib import Path

from soundsgood.diagnostics import get_logger


LOGGER = get_logger("catalog.cache")


def load_cache(path: Path, directory: str) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as cache_file:
            cache = json.load(cache_file)
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Ignoring unreadable catalog cache", exc_info=True)
        return {}
    return cache if cache.get("directory") == directory else {}


def save_cache(
    path: Path,
    version: int,
    directory: str,
    records: list[dict],
    directory_records: list[dict] | None = None,
):
    data = {
        "version": version,
        "directory": directory,
        "directories": directory_records or [],
        "songs": records,
    }
    temporary_path = path.with_suffix(".json.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as cache_file:
            json.dump(data, cache_file, ensure_ascii=False, indent=2)
            cache_file.flush()
            os.fsync(cache_file.fileno())
        os.replace(temporary_path, path)
    except OSError:
        LOGGER.exception("Could not persist catalog cache")
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def file_stat(path: str) -> dict | None:
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def record_matches_file(record: dict | None, stat: dict) -> bool:
    return bool(
        record
        and record.get("mtime_ns") == stat["mtime_ns"]
        and record.get("size") == stat["size"]
    )
