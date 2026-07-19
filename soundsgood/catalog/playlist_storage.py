# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Pure validation and atomic persistence helpers for saved playlists."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote, urlparse


FORMAT_VERSION = 1
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_PLAYLISTS = 10_000
MAX_ENTRIES = 100_000
MAX_NAME_LENGTH = 120


class PlaylistStorageError(ValueError):
    """Raised when saved playlist data cannot be trusted or persisted."""


def normalize_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise PlaylistStorageError("Playlist name cannot be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise PlaylistStorageError(
            f"Playlist name cannot exceed {MAX_NAME_LENGTH} characters"
        )
    if any(character in name for character in "\r\n\0"):
        raise PlaylistStorageError("Playlist name contains invalid characters")
    return name


def normalize_document(document: object) -> dict:
    if not isinstance(document, dict):
        raise PlaylistStorageError("Playlist document must be an object")
    if document.get("version") != FORMAT_VERSION:
        raise PlaylistStorageError("Unsupported playlist document version")

    raw_playlists = document.get("playlists")
    if not isinstance(raw_playlists, list):
        raise PlaylistStorageError("Playlist document has no playlist list")
    if len(raw_playlists) > MAX_PLAYLISTS:
        raise PlaylistStorageError("Playlist document contains too many playlists")

    identifiers = set()
    names = set()
    playlists = []
    for raw_playlist in raw_playlists:
        playlist = _normalize_playlist(raw_playlist)
        identifier = playlist["id"]
        folded_name = playlist["name"].casefold()
        if identifier in identifiers:
            raise PlaylistStorageError("Playlist identifiers must be unique")
        if folded_name in names:
            raise PlaylistStorageError("Playlist names must be unique")
        identifiers.add(identifier)
        names.add(folded_name)
        playlists.append(playlist)
    return {"version": FORMAT_VERSION, "playlists": playlists}


def _normalize_playlist(value: object) -> dict:
    if not isinstance(value, dict):
        raise PlaylistStorageError("Playlist record must be an object")
    identifier = _required_string(value.get("id"), "Playlist identifier")
    name = normalize_name(value.get("name"))
    updated_at = str(value.get("updated_at") or "")
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list):
        raise PlaylistStorageError("Playlist entries must be a list")
    if len(raw_entries) > MAX_ENTRIES:
        raise PlaylistStorageError("Playlist contains too many entries")
    entry_ids = set()
    entries = []
    for raw_entry in raw_entries:
        entry = _normalize_entry(raw_entry)
        if entry["id"] in entry_ids:
            raise PlaylistStorageError("Playlist entry identifiers must be unique")
        entry_ids.add(entry["id"])
        entries.append(entry)
    return {
        "id": identifier,
        "name": name,
        "updated_at": updated_at,
        "entries": entries,
    }


def _normalize_entry(value: object) -> dict:
    if not isinstance(value, dict):
        raise PlaylistStorageError("Playlist entry must be an object")
    identifier = _required_string(value.get("id"), "Playlist entry identifier")
    url = _required_string(value.get("url"), "Playlist entry URL")
    if not url.startswith("file://"):
        raise PlaylistStorageError("Only local file URLs can be saved")
    try:
        duration = max(0, int(value.get("duration") or 0))
    except (TypeError, ValueError) as error:
        raise PlaylistStorageError("Playlist entry duration is invalid") from error
    return {
        "id": identifier,
        "url": url,
        "title": str(value.get("title") or ""),
        "artist": str(value.get("artist") or ""),
        "album": str(value.get("album") or ""),
        "duration": duration,
        "thumbnail": str(value.get("thumbnail") or ""),
    }


def _required_string(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized or "\0" in normalized:
        raise PlaylistStorageError(f"{label} is invalid")
    return normalized


def load_document(path: Path) -> dict:
    if not path.exists():
        return {"version": FORMAT_VERSION, "playlists": []}
    try:
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            raise PlaylistStorageError("Playlist document is too large")
        with path.open("r", encoding="utf-8") as source:
            document = json.load(source)
    except PlaylistStorageError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PlaylistStorageError("Saved playlists could not be read") from error
    return normalize_document(document)


def save_document(path: Path, document: object):
    normalized = normalize_document(document)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as destination:
            json.dump(normalized, destination, ensure_ascii=False, indent=2)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PlaylistStorageError("Saved playlists could not be written") from error


def export_m3u8(path: Path, entries: list[dict], relative: bool = True):
    lines = ["#EXTM3U"]
    base = path.parent.resolve()
    for entry in entries:
        normalized = _normalize_entry(entry)
        duration = normalized["duration"] if normalized["duration"] else -1
        display = normalized["title"]
        if normalized["artist"]:
            display = f"{normalized['artist']} - {display}"
        lines.append(f"#EXTINF:{duration},{display}")
        lines.append(_export_location(normalized["url"], base, relative))

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(lines) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PlaylistStorageError("Playlist export could not be written") from error


def _export_location(url: str, base: Path, relative: bool) -> str:
    parsed = urlparse(url)
    file_path = Path(unquote(parsed.path))
    if relative:
        try:
            return os.path.relpath(file_path, base)
        except ValueError:
            pass
    return str(file_path)
