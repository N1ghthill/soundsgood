# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Persistent playlist domain service, independent from the playback queue."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from gi.repository import Gio, GLib, GObject

from soundsgood.catalog.playlist_storage import (
    FORMAT_VERSION,
    PlaylistStorageError,
    export_m3u8,
    load_document,
    normalize_name,
    save_document,
)
from soundsgood.diagnostics import get_logger
from soundsgood.models import Playlist, PlaylistEntry, Song


LOGGER = get_logger("playlists")


class PlaylistManager(GObject.GObject):
    """Own saved playlist models and serialize changes away from the GTK loop."""

    __gsignals__ = {
        "loaded": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    loaded = GObject.Property(type=bool, default=False)

    def __init__(self, path: Path | None = None, load_async: bool = True):
        super().__init__()
        data_home = Path(
            os.environ.get("XDG_DATA_HOME") or GLib.get_user_data_dir()
        )
        self._path = path or data_home / "soundsgood" / "playlists.json"
        self._playlists = Gio.ListStore(item_type=Playlist)
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="soundsgood-playlists",
        )
        self._lock = Lock()
        self._save_generation = 0
        self._dirty = False
        self._closed = False
        self._load_future = None
        if load_async:
            self._load_future = self._executor.submit(load_document, self._path)
            self._load_future.add_done_callback(self._load_finished)
        else:
            self._apply_document(load_document(self._path))

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def playlists(self):
        return self._playlists

    def _load_finished(self, future):
        try:
            document = future.result()
        except Exception as error:
            LOGGER.warning("Could not load saved playlists", exc_info=True)
            GLib.idle_add(self._load_failed, str(error))
            return
        GLib.idle_add(self._apply_document, document)

    def _load_failed(self, message: str):
        if self._closed:
            return GLib.SOURCE_REMOVE
        self.props.loaded = True
        self.emit("error", message)
        self.emit("loaded")
        return GLib.SOURCE_REMOVE

    def _apply_document(self, document: dict):
        if self._closed:
            return GLib.SOURCE_REMOVE
        self._playlists.remove_all()
        for record in document["playlists"]:
            entries = Gio.ListStore(item_type=PlaylistEntry)
            for entry_record in record["entries"]:
                entries.append(self._entry_from_record(entry_record))
            self._playlists.append(
                Playlist(
                    identifier=record["id"],
                    name=record["name"],
                    entries=entries,
                    entry_count=entries.get_n_items(),
                    updated_at=record["updated_at"],
                )
            )
        self.props.loaded = True
        self.emit("loaded")
        return GLib.SOURCE_REMOVE

    def create(self, name: str, songs: list[Song] | None = None) -> Playlist:
        self._require_loaded()
        normalized_name = self._available_name(normalize_name(name))
        entries = Gio.ListStore(item_type=PlaylistEntry)
        playlist = Playlist(
            identifier=str(uuid4()),
            name=normalized_name,
            entries=entries,
            entry_count=0,
            updated_at=self._now(),
        )
        self._playlists.append(playlist)
        if songs:
            if not self.add_songs(playlist, songs):
                self._record_change(playlist)
        else:
            self._record_change(playlist)
        return playlist

    def rename(self, playlist: Playlist, name: str):
        self._require_loaded()
        normalized_name = normalize_name(name)
        self._ensure_member(playlist)
        for other in self._iter_playlists():
            if other is not playlist and other.props.name.casefold() == normalized_name.casefold():
                raise PlaylistStorageError("A playlist with this name already exists")
        playlist.props.name = normalized_name
        self._record_change(playlist)

    def delete(self, playlist: Playlist):
        self._require_loaded()
        index = self._playlist_index(playlist)
        if index < 0:
            raise PlaylistStorageError("Playlist does not belong to this library")
        self._playlists.remove(index)
        self._dirty = True
        self._schedule_save()
        self.emit("changed", playlist)

    def add_songs(self, playlist: Playlist, songs: list[Song]) -> int:
        self._require_loaded()
        self._ensure_member(playlist)
        added = 0
        existing_urls = {
            playlist.props.entries.get_item(index).props.url
            for index in range(playlist.props.entries.get_n_items())
        }
        for song in songs:
            if (
                not isinstance(song, Song)
                or not song.props.url.startswith("file://")
                or song.props.url in existing_urls
            ):
                continue
            playlist.props.entries.append(self._entry_from_song(song))
            existing_urls.add(song.props.url)
            added += 1
        if added:
            playlist.props.entry_count = playlist.props.entries.get_n_items()
            self._record_change(playlist)
        return added

    def remove_entry(self, playlist: Playlist, position: int):
        self._require_loaded()
        self._ensure_member(playlist)
        if position < 0 or position >= playlist.props.entries.get_n_items():
            raise IndexError(position)
        playlist.props.entries.remove(position)
        playlist.props.entry_count = playlist.props.entries.get_n_items()
        self._record_change(playlist)

    def move_entry(self, playlist: Playlist, old_position: int, new_position: int):
        self._require_loaded()
        self._ensure_member(playlist)
        count = playlist.props.entries.get_n_items()
        if not 0 <= old_position < count or not 0 <= new_position < count:
            raise IndexError((old_position, new_position))
        if old_position == new_position:
            return
        entry = playlist.props.entries.get_item(old_position)
        playlist.props.entries.remove(old_position)
        playlist.props.entries.insert(new_position, entry)
        self._record_change(playlist)

    def resolved_songs(self, playlist: Playlist, library) -> list[Song]:
        library_songs = {song.props.url: song for song in library.get_all_songs()}
        songs = []
        entries = playlist.props.entries
        for index in range(entries.get_n_items()):
            entry = entries.get_item(index)
            song = library_songs.get(entry.props.url)
            if song is not None:
                songs.append(song)
            elif entry.props.available:
                songs.append(
                    Song(
                        title=entry.props.title,
                        artist=entry.props.artist,
                        album=entry.props.album,
                        duration=entry.props.duration,
                        thumbnail=entry.props.thumbnail or None,
                        url=entry.props.url,
                    )
                )
        return songs

    def refresh_availability(self, library):
        known = {song.props.url for song in library.get_all_songs()}
        records = []
        for playlist in self._iter_playlists():
            entries = playlist.props.entries
            for index in range(entries.get_n_items()):
                entry = entries.get_item(index)
                records.append((entry, entry.props.url, entry.props.url in known))

        def check():
            results = []
            for entry, url, is_known in records:
                available = is_known or Gio.File.new_for_uri(url).query_exists(None)
                results.append((entry, available))
            return results

        future = self._executor.submit(check)
        future.add_done_callback(
            lambda completed: GLib.idle_add(
                self._apply_availability,
                completed.result(),
            )
        )

    def _apply_availability(self, results):
        if self._closed:
            return GLib.SOURCE_REMOVE
        for entry, available in results:
            entry.props.available = available
        return GLib.SOURCE_REMOVE

    def export_async(self, playlist: Playlist, path: Path, callback=None):
        self._ensure_member(playlist)
        entries = [
            self._entry_record(playlist.props.entries.get_item(index))
            for index in range(playlist.props.entries.get_n_items())
        ]
        future = self._executor.submit(export_m3u8, path, entries, True)
        if callback:
            future.add_done_callback(
                lambda completed: GLib.idle_add(callback, completed.exception())
            )

    def import_async(self, file: Gio.File, library, callback=None):
        """Read one external playlist off the GTK loop and save it by name."""

        def read():
            return library.create_songs_for_file(file)

        def finished(future):
            error = future.exception()
            songs = [] if error else future.result()
            GLib.idle_add(self._finish_import, file, songs, error, callback)

        self._executor.submit(read).add_done_callback(finished)

    def _finish_import(self, file, songs, error, callback):
        playlist = None
        if error is None and songs:
            basename = file.get_basename() or "Imported playlist"
            try:
                playlist = self.create(Path(basename).stem, songs)
            except Exception as create_error:
                error = create_error
        elif error is None:
            error = PlaylistStorageError("The playlist contains no playable local songs")
        if callback:
            callback(playlist, error)
        return GLib.SOURCE_REMOVE

    def add_files_async(self, playlist: Playlist, files, library, callback=None):
        """Discover selected local audio files without blocking the GTK loop."""

        self._ensure_member(playlist)
        file_list = list(files)

        def read():
            songs = []
            for file in file_list:
                songs.extend(library.create_songs_for_file(file))
            return songs

        def finished(future):
            error = future.exception()
            songs = [] if error else future.result()
            GLib.idle_add(
                self._finish_add_files,
                playlist,
                songs,
                error,
                callback,
            )

        self._executor.submit(read).add_done_callback(finished)

    def _finish_add_files(self, playlist, songs, error, callback):
        added = 0
        if error is None:
            try:
                added = self.add_songs(playlist, songs)
            except Exception as add_error:
                error = add_error
        if callback:
            callback(added, error)
        return GLib.SOURCE_REMOVE

    def _record_change(self, playlist: Playlist):
        playlist.props.updated_at = self._now()
        self._dirty = True
        self._schedule_save()
        self.emit("changed", playlist)

    def _schedule_save(self):
        if self._closed:
            return
        document = self._document()
        with self._lock:
            self._save_generation += 1
            generation = self._save_generation

        def save_latest():
            with self._lock:
                if generation != self._save_generation or self._closed:
                    return
            save_document(self._path, document)

        future = self._executor.submit(save_latest)
        future.add_done_callback(self._save_finished)

    def _save_finished(self, future):
        error = future.exception()
        if error is not None:
            LOGGER.error("Could not save playlists: %s", error)
            GLib.idle_add(self.emit, "error", str(error))

    def flush(self):
        if self._closed:
            return
        if not self.props.loaded:
            if self._load_future is not None:
                self._load_future.result()
            return
        if not self._dirty:
            return
        document = self._document()
        self._executor.submit(save_document, self._path, document).result()

    def shutdown(self):
        if self._closed:
            return
        try:
            self.flush()
        except PlaylistStorageError:
            LOGGER.warning("Could not flush playlists during shutdown", exc_info=True)
        self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _document(self):
        return {
            "version": FORMAT_VERSION,
            "playlists": [self._playlist_record(item) for item in self._iter_playlists()],
        }

    def _playlist_record(self, playlist: Playlist) -> dict:
        entries = playlist.props.entries
        return {
            "id": playlist.props.identifier,
            "name": playlist.props.name,
            "updated_at": playlist.props.updated_at,
            "entries": [
                self._entry_record(entries.get_item(index))
                for index in range(entries.get_n_items())
            ],
        }

    def _entry_record(self, entry: PlaylistEntry) -> dict:
        return {
            "id": entry.props.identifier,
            "url": entry.props.url,
            "title": entry.props.title,
            "artist": entry.props.artist,
            "album": entry.props.album,
            "duration": entry.props.duration,
            "thumbnail": entry.props.thumbnail or "",
        }

    def _entry_from_record(self, record: dict) -> PlaylistEntry:
        return PlaylistEntry(
            identifier=record["id"],
            url=record["url"],
            title=record["title"],
            artist=record["artist"],
            album=record["album"],
            duration=record["duration"],
            thumbnail=record["thumbnail"] or None,
            available=True,
        )

    def _entry_from_song(self, song: Song) -> PlaylistEntry:
        return PlaylistEntry(
            identifier=str(uuid4()),
            url=song.props.url,
            title=song.props.title,
            artist=song.props.artist,
            album=song.props.album,
            duration=song.props.duration,
            thumbnail=song.props.thumbnail,
            available=True,
        )

    def _available_name(self, preferred: str) -> str:
        existing = {playlist.props.name.casefold() for playlist in self._iter_playlists()}
        if preferred.casefold() not in existing:
            return preferred
        suffix = 2
        while f"{preferred} {suffix}".casefold() in existing:
            suffix += 1
        return f"{preferred} {suffix}"

    def _ensure_member(self, playlist: Playlist):
        if self._playlist_index(playlist) < 0:
            raise PlaylistStorageError("Playlist does not belong to this library")

    def _require_loaded(self):
        if self._closed:
            raise PlaylistStorageError("Saved playlists are shutting down")
        if not self.props.loaded:
            raise PlaylistStorageError("Saved playlists are still loading")

    def _playlist_index(self, playlist: Playlist) -> int:
        for index, item in enumerate(self._iter_playlists()):
            if item is playlist:
                return index
        return -1

    def _iter_playlists(self):
        return (
            self._playlists.get_item(index)
            for index in range(self._playlists.get_n_items())
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
