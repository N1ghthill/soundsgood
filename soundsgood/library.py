# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations
import gi
import hashlib
import json
import os
import mimetypes
import re
import subprocess
import unicodedata
from gettext import gettext as _
from typing import Optional
from pathlib import Path

gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")

from gi.repository import GObject, GLib, Gio, Gst, GstPbutils

from soundsgood.models import Song, Album, Artist, LibraryState


CACHE_VERSION = 2

# Supported audio formats
AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac",
    ".wma", ".opus", ".ape", ".aiff", ".dsf", ".dff",
}
PLAYLIST_EXTENSIONS = {".m3u", ".m3u8", ".pls"}


class Library(GObject.GObject):
    """Scans and manages the music library."""

    __gsignals__ = {
        "scan-started": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "scan-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "scan-error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "song-added": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    songs_available = GObject.Property(type=bool, default=False)
    scan_state = GObject.Property(type=int, default=int(LibraryState.EMPTY))
    status_message = GObject.Property(type=str, default="")

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._settings = application.props.settings
        self._is_scanning = False
        self._current_directory = ""
        self._monitors = []
        self._rescan_source_id = 0
        self._refresh_metadata_scan = False

        # Data stores
        self._songs = Gio.ListStore.new(Song)
        self._albums = Gio.ListStore.new(Album)
        self._artists = Gio.ListStore.new(Artist)

        # Indexes for fast lookup
        self._album_map: dict[str, Album] = {}
        self._artist_map: dict[str, Artist] = {}

        mimetypes.init()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def songs(self) -> Gio.ListStore:
        return self._songs

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def albums(self) -> Gio.ListStore:
        return self._albums

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def artists(self) -> Gio.ListStore:
        return self._artists

    def scan(
        self,
        directory: Optional[str] = None,
        force: bool = False,
        refresh_metadata: bool = False,
    ):
        """Scan a directory for music files."""
        if self._is_scanning:
            return

        if directory is None:
            directory = self._settings.get_string("music-dir")
            if not directory:
                directory = self._default_music_dir()

        if not directory or not os.path.isdir(directory):
            message = _("Music folder not found")
            self._set_scan_state(LibraryState.ERROR, message)
            self.emit("scan-error", message)
            return

        self._current_directory = directory

        if not force:
            cache = self._load_cache(directory)
            if "songs" in cache and self._cache_matches_filesystem(cache):
                self._setup_cached_monitors(directory, cache)
                songs = [
                    self._song_from_record(record)
                    for record in cache.get("songs", [])
                ]
                self._apply_scan_results(songs)
                return

        self._setup_monitors(directory)
        self._is_scanning = True
        self._refresh_metadata_scan = refresh_metadata
        self._set_scan_state(LibraryState.SCANNING, _("Scanning music..."))
        self.emit("scan-started")

        GLib.Thread.new("scanner", self._scan_directory, directory)

    def _scan_directory(self, directory: str):
        """Scan directory recursively for audio files."""
        audio_files = []
        cache = self._load_cache(directory)
        cached_records = {
            record.get("path"): record
            for record in cache.get("songs", [])
            if record.get("path")
        }
        next_records = []
        directory_records = []
        cache_dirty = refresh_metadata = self._refresh_metadata_scan

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            root_stat = self._file_stat(root)
            if root_stat is not None:
                directory_records.append({
                    "path": root,
                    "mtime_ns": root_stat["mtime_ns"],
                    "size": root_stat["size"],
                })

            for filename in sorted(files):
                ext = os.path.splitext(filename)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    filepath = os.path.join(root, filename)
                    audio_files.append(filepath)

        for filepath in audio_files:
            stat = self._file_stat(filepath)
            if stat is None:
                continue

            cached_record = cached_records.get(filepath)
            if not refresh_metadata and self._record_matches_file(cached_record, stat):
                song = self._song_from_record(cached_record)
            else:
                song = self._create_song_from_file(filepath)
                cache_dirty = True

            if song:
                next_records.append(self._record_from_song(song, filepath, stat))

        if cache.get("version") != CACHE_VERSION or "songs" not in cache:
            cache_dirty = True
        if cache.get("directories") != directory_records:
            cache_dirty = True
        if set(cached_records) != set(audio_files):
            cache_dirty = True
        if cache_dirty:
            self._save_cache(directory, next_records, directory_records)

        GLib.idle_add(
            self._apply_scan_results,
            [self._song_from_record(record) for record in next_records],
        )

    def _setup_monitors(self, directory: str):
        self._clear_monitors()

        for root, dirs, _files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            try:
                monitor = Gio.File.new_for_path(root).monitor_directory(
                    Gio.FileMonitorFlags.NONE,
                    None,
                )
            except GLib.Error:
                continue

            monitor.connect("changed", self._on_directory_changed)
            self._monitors.append(monitor)

    def _clear_monitors(self):
        for monitor in self._monitors:
            monitor.cancel()
        self._monitors.clear()

    def _setup_cached_monitors(self, directory: str, cache: dict):
        self._clear_monitors()

        paths = {directory}
        for record in cache.get("directories", []):
            path = record.get("path")
            if path:
                paths.add(path)
        for record in cache.get("songs", []):
            path = record.get("path")
            if path:
                paths.add(os.path.dirname(path))

        for path in sorted(paths):
            if not os.path.isdir(path):
                continue
            try:
                monitor = Gio.File.new_for_path(path).monitor_directory(
                    Gio.FileMonitorFlags.NONE,
                    None,
                )
            except GLib.Error:
                continue

            monitor.connect("changed", self._on_directory_changed)
            self._monitors.append(monitor)

    def _on_directory_changed(self, _monitor, _file, _other_file, event_type):
        ignored_events = {
            Gio.FileMonitorEvent.ATTRIBUTE_CHANGED,
            Gio.FileMonitorEvent.PRE_UNMOUNT,
            Gio.FileMonitorEvent.UNMOUNTED,
        }
        if event_type in ignored_events:
            return

        if self._rescan_source_id:
            GLib.source_remove(self._rescan_source_id)

        self._rescan_source_id = GLib.timeout_add_seconds(2, self._rescan_current_directory)

    def _rescan_current_directory(self):
        if self._is_scanning:
            return GLib.SOURCE_CONTINUE

        self._rescan_source_id = 0
        if self._current_directory:
            self.scan(self._current_directory, force=True)

        return GLib.SOURCE_REMOVE

    def _create_song_from_file(self, filepath: str) -> Optional[Song]:
        """Create a Song object from a file path."""
        uri = Path(filepath).resolve().as_uri()
        filename = os.path.basename(filepath)
        name, _ext = os.path.splitext(filename)

        artist = _("Unknown Artist")
        title = name
        album_title = self._album_from_path(filepath)
        album_artist = artist
        duration = 0
        track_number = 0
        disc_number = 1
        year = ""
        genre = ""
        thumbnail = ""
        fallback_artist, fallback_title, fallback_track = self._metadata_from_filename(name)

        metadata = self._discover_metadata(uri)
        if metadata:
            title = metadata.get("title") or fallback_title
            artist = metadata.get("artist") or fallback_artist
            album_title = metadata.get("album") or album_title
            album_artist = metadata.get("album_artist") or artist
            duration = metadata.get("duration") or 0
            track_number = metadata.get("track_number") or fallback_track
            disc_number = metadata.get("disc_number") or 1
            year = metadata.get("year") or ""
            genre = metadata.get("genre") or ""
            thumbnail = metadata.get("thumbnail") or ""
        else:
            artist = fallback_artist
            title = fallback_title
            track_number = fallback_track
            album_artist = artist

        if not thumbnail:
            thumbnail = self._cover_from_directory(filepath)

        return Song(
            title=title,
            artist=artist,
            album=album_title,
            album_artist=album_artist,
            duration=duration,
            track_number=track_number,
            disc_number=disc_number,
            year=year,
            genre=genre,
            thumbnail=thumbnail,
            url=uri,
        )

    def create_song_for_file(self, file: Gio.File) -> Optional[Song]:
        """Create a Song for an external file opened by the desktop."""
        songs = self.create_songs_for_file(file)
        return songs[0] if songs else None

    def create_songs_for_file(self, file: Gio.File) -> list[Song]:
        """Create Songs for an external audio file or playlist."""
        path = file.get_path()
        if path:
            ext = os.path.splitext(path)[1].lower()
            if ext in PLAYLIST_EXTENSIONS:
                return self._songs_from_playlist_path(path)
            if ext not in AUDIO_EXTENSIONS:
                return []
            song = self._create_song_from_file(path)
            return [song] if song is not None else []

        uri = file.get_uri()
        if not uri:
            return []

        basename = file.get_basename() or uri.rsplit("/", 1)[-1]
        title, _ext = os.path.splitext(basename)
        if _ext.lower() in PLAYLIST_EXTENSIONS:
            return []

        return [
            Song(
                title=title or basename,
                artist=_("Unknown Artist"),
                album=_("Unknown Album"),
                album_artist=_("Unknown Artist"),
                url=uri,
            )
        ]

    def _songs_from_playlist_path(self, path: str) -> list[Song]:
        extension = os.path.splitext(path)[1].lower()
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        if extension == ".pls":
            entries = self._pls_entries(text)
        else:
            entries = self._m3u_entries(text)

        songs = []
        playlist_dir = Path(path).parent
        for entry in entries:
            file = self._playlist_entry_file(entry, playlist_dir)
            if file is None:
                continue
            song = self.create_song_for_file(file)
            if song is not None:
                songs.append(song)

        return songs

    def _m3u_entries(self, text: str) -> list[str]:
        entries = []
        for line in text.splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            entries.append(entry)
        return entries

    def _pls_entries(self, text: str) -> list[str]:
        entries = {}
        for line in text.splitlines():
            key, separator, value = line.partition("=")
            if not separator or not key.casefold().startswith("file"):
                continue
            suffix = key[4:]
            if not suffix.isdigit():
                continue
            value = value.strip()
            if value:
                entries[int(suffix)] = value
        return [entries[index] for index in sorted(entries)]

    def _playlist_entry_file(self, entry: str, playlist_dir: Path) -> Gio.File | None:
        if "://" in entry:
            if entry.startswith("file://"):
                return Gio.File.new_for_uri(entry)
            return None

        path = Path(entry).expanduser()
        if not path.is_absolute():
            path = playlist_dir / path
        return Gio.File.new_for_path(str(path))

    def _discover_metadata(self, uri: str) -> Optional[dict]:
        """Read tags and duration with GStreamer Discoverer."""
        try:
            discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
            info = discoverer.discover_uri(uri)
        except GLib.Error:
            return None

        tags = info.get_tags()
        duration = int(info.get_duration() / Gst.SECOND) if info.get_duration() else 0

        if tags is None and duration == 0:
            return None

        return {
            "title": self._tag_string(tags, Gst.TAG_TITLE),
            "artist": self._tag_string(tags, Gst.TAG_ARTIST),
            "album": self._tag_string(tags, Gst.TAG_ALBUM),
            "album_artist": self._tag_string(tags, Gst.TAG_ALBUM_ARTIST),
            "track_number": self._tag_uint(tags, Gst.TAG_TRACK_NUMBER),
            "disc_number": self._tag_uint(tags, Gst.TAG_ALBUM_VOLUME_NUMBER),
            "year": self._tag_date(tags),
            "genre": self._tag_string(tags, Gst.TAG_GENRE),
            "thumbnail": self._extract_cover(tags, uri),
            "duration": duration,
        }

    def _tag_string(self, tags, key: str) -> str:
        if tags is None:
            return ""

        try:
            success, value = tags.get_string(key)
        except (TypeError, AttributeError):
            return ""

        return value if success and value else ""

    def _tag_uint(self, tags, key: str) -> int:
        if tags is None:
            return 0

        try:
            success, value = tags.get_uint(key)
        except (TypeError, AttributeError):
            return 0

        return int(value) if success else 0

    def _tag_date(self, tags) -> str:
        if tags is None:
            return ""

        for key in (Gst.TAG_DATE_TIME, Gst.TAG_DATE):
            try:
                success, value = tags.get_date_time(key)
            except (TypeError, AttributeError):
                success = False
                value = None

            if success and value:
                return str(value.get_year())

        return ""

    def _extract_cover(self, tags, uri: str) -> str:
        if tags is None:
            return ""

        sample = self._tag_sample(tags, Gst.TAG_IMAGE)
        if sample is None:
            sample = self._tag_sample(tags, Gst.TAG_PREVIEW_IMAGE)
        if sample is None:
            return ""

        buffer = sample.get_buffer()
        caps = sample.get_caps()
        if buffer is None or caps is None or caps.get_size() == 0:
            return ""

        mime = caps.get_structure(0).get_name()
        extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }.get(mime)
        if extension is None:
            return ""

        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return ""

        try:
            cache_dir = Path(GLib.get_user_cache_dir()) / "soundsgood" / "covers"
            cache_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
            cover_path = cache_dir / f"{digest}{extension}"
            if not cover_path.exists():
                cover_path.write_bytes(map_info.data)
            return str(cover_path)
        finally:
            buffer.unmap(map_info)

    def _tag_sample(self, tags, key: str):
        try:
            result = tags.get_sample(key)
        except (TypeError, AttributeError):
            return None

        if isinstance(result, tuple):
            success, sample = result
            return sample if success else None

        return result

    def _metadata_from_filename(self, name: str) -> tuple[str, str, int]:
        artist = _("Unknown Artist")
        title = name
        track_number = 0

        if " - " in name:
            left, right = [part.strip() for part in name.split(" - ", 1)]
            if left.isdigit():
                track_number = int(left)
                title = right
            else:
                artist = left
                title = right

        if title and title[0].isdigit():
            match = re.match(r"(\d+)[\s.\-)]*(.*)", title)
            if match:
                track_number = int(match.group(1))
                title = match.group(2).strip() or title

        return artist, title, track_number

    def _album_from_path(self, filepath: str) -> str:
        parent_dir = os.path.basename(os.path.dirname(filepath))
        music_dirs = {
            os.path.basename(os.path.expanduser("~/Music")),
            os.path.basename(self._default_music_dir()),
        }
        return parent_dir if parent_dir and parent_dir not in music_dirs else _("Unknown Album")

    def _default_music_dir(self) -> str:
        try:
            result = subprocess.run(
                ["xdg-user-dir", "MUSIC"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            result = None

        if result and result.returncode == 0:
            directory = result.stdout.strip()
            if directory:
                return directory

        return os.path.expanduser("~/Music")

    def _cover_from_directory(self, filepath: str) -> str:
        directory = Path(filepath).parent
        preferred_names = (
            "cover",
            "folder",
            "front",
            "album",
            "artwork",
        )
        extensions = (".jpg", ".jpeg", ".png", ".webp")

        for name in preferred_names:
            for extension in extensions:
                for candidate in (
                    directory / f"{name}{extension}",
                    directory / f"{name.capitalize()}{extension}",
                ):
                    if candidate.is_file():
                        return str(candidate)

        try:
            candidates = sorted(directory.iterdir())
        except OSError:
            return ""

        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in extensions:
                return str(candidate)

        return ""

    def _cache_path(self) -> Path:
        cache_dir = Path(GLib.get_user_cache_dir()) / "soundsgood"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "library.json"

    def _load_cache(self, directory: str) -> dict:
        cache_path = self._cache_path()
        if not cache_path.exists():
            return {}

        try:
            with cache_path.open("r", encoding="utf-8") as cache_file:
                cache = json.load(cache_file)
        except (OSError, json.JSONDecodeError):
            return {}

        if cache.get("directory") != directory:
            return {}

        return cache

    def _save_cache(
        self,
        directory: str,
        records: list[dict],
        directory_records: list[dict] | None = None,
    ):
        cache_path = self._cache_path()
        data = {
            "version": CACHE_VERSION,
            "directory": directory,
            "directories": directory_records or [],
            "songs": records,
        }

        try:
            with cache_path.open("w", encoding="utf-8") as cache_file:
                json.dump(data, cache_file, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _file_stat(self, filepath: str) -> dict | None:
        try:
            stat = os.stat(filepath)
        except OSError:
            return None

        return {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }

    def _record_matches_file(self, record: Optional[dict], stat: dict) -> bool:
        if not record:
            return False

        return (
            record.get("mtime_ns") == stat["mtime_ns"]
            and record.get("size") == stat["size"]
        )

    def _cache_matches_filesystem(self, cache: dict) -> bool:
        if cache.get("version") != CACHE_VERSION:
            return False
        if "directories" not in cache:
            return False

        for record in cache.get("directories", []):
            path = record.get("path")
            stat = self._file_stat(path) if path else None
            if stat is None or not self._record_matches_file(record, stat):
                return False

        for record in cache.get("songs", []):
            path = record.get("path")
            stat = self._file_stat(path) if path else None
            if stat is None or not self._record_matches_file(record, stat):
                return False

        return True

    def _record_from_song(self, song: Song, filepath: str, stat: dict) -> dict:
        return {
            "path": filepath,
            "mtime_ns": stat["mtime_ns"],
            "size": stat["size"],
            "title": song.props.title,
            "artist": song.props.artist,
            "album": song.props.album,
            "album_artist": song.props.album_artist,
            "duration": song.props.duration,
            "track_number": song.props.track_number,
            "disc_number": song.props.disc_number,
            "year": song.props.year,
            "genre": song.props.genre,
            "url": song.props.url,
            "thumbnail": song.props.thumbnail or "",
        }

    def _song_from_record(self, record: dict) -> Song:
        return Song(
            title=record.get("title", ""),
            artist=record.get("artist", ""),
            album=record.get("album", ""),
            album_artist=record.get("album_artist", ""),
            duration=int(record.get("duration") or 0),
            track_number=int(record.get("track_number") or 0),
            disc_number=int(record.get("disc_number") or 1),
            year=record.get("year", ""),
            genre=record.get("genre", ""),
            url=record.get("url", ""),
            thumbnail=record.get("thumbnail") or "",
        )

    def get_all_songs(self) -> list[Song]:
        """Return songs as a regular Python list."""
        return [
            self._songs.get_item(i)
            for i in range(self._songs.get_n_items())
        ]

    def get_songs_for_artist(self, artist_name: str) -> Gio.ListStore:
        """Get all songs for a specific artist."""
        songs = Gio.ListStore.new(Song)
        for i in range(self._songs.get_n_items()):
            song = self._songs.get_item(i)
            if song.props.artist == artist_name or song.props.album_artist == artist_name:
                songs.append(song)

        return songs

    def _sort_models(self):
        self._songs.sort(
            lambda a, b: (
                self._song_sort_key(a) > self._song_sort_key(b)
            ) - (
                self._song_sort_key(a) < self._song_sort_key(b)
            )
        )
        self._albums.sort(
            lambda a, b: (
                (a.props.artist.lower(), a.props.year, a.props.title.lower())
                > (b.props.artist.lower(), b.props.year, b.props.title.lower())
            ) - (
                (a.props.artist.lower(), a.props.year, a.props.title.lower())
                < (b.props.artist.lower(), b.props.year, b.props.title.lower())
            )
        )
        self._artists.sort(
            lambda a, b: (a.props.name.lower() > b.props.name.lower())
            - (a.props.name.lower() < b.props.name.lower())
        )

        for album in self._album_map.values():
            album.props.songs.sort(
                lambda a, b: (
                    self._album_song_sort_key(a) > self._album_song_sort_key(b)
                ) - (
                    self._album_song_sort_key(a) < self._album_song_sort_key(b)
                )
            )

    def _song_sort_key(self, song: Song):
        return (
            song.props.album_artist.lower(),
            song.props.album.lower(),
            self._album_song_sort_key(song),
        )

    def _album_song_sort_key(self, song: Song):
        track_number = song.props.track_number or 9999
        return (
            song.props.disc_number or 1,
            track_number,
            song.props.title.lower(),
        )

    def _finish_scan(self):
        """Finalize scan."""
        self._sort_models()
        self.props.songs_available = self._songs.get_n_items() > 0
        self._is_scanning = False
        self._refresh_metadata_scan = False
        if self.props.songs_available:
            self._set_scan_state(LibraryState.READY, "")
        else:
            self._set_scan_state(LibraryState.EMPTY, _("No music found"))
        self.emit("scan-finished")

    def _set_scan_state(self, state: LibraryState, message: str = ""):
        self.props.scan_state = int(state)
        self.props.status_message = message

    def _apply_scan_results(self, songs: list[Song]):
        """Apply a scanned library snapshot without clearing unchanged songs."""
        incoming_by_url = {
            song.props.url: song
            for song in songs
            if song.props.url
        }
        existing_by_url = {
            song.props.url: index
            for index, song in enumerate(self.get_all_songs())
            if song.props.url
        }

        for url in set(existing_by_url) - set(incoming_by_url):
            index = self._find_song_index_by_url(url)
            if index >= 0:
                removed_song = self._songs.get_item(index)
                self._songs.remove(index)
                self._remove_song_from_aggregates(removed_song)

        for song in songs:
            index = self._find_song_index_by_url(song.props.url)
            if index < 0:
                self._songs.append(song)
                self._add_song_to_aggregates(song)
                self.emit("song-added", song)
                continue

            existing_song = self._songs.get_item(index)
            if self._song_signature(existing_song) != self._song_signature(song):
                self._songs.remove(index)
                self._remove_song_from_aggregates(existing_song)
                self._songs.insert(index, song)
                self._add_song_to_aggregates(song)
                self.emit("song-added", song)

        self._finish_scan()

        return GLib.SOURCE_REMOVE

    def _add_song(self, song: Song):
        """Add a song to the library (called from main thread)."""
        self._songs.append(song)
        self._add_song_to_aggregates(song)
        self.emit("song-added", song)

    def _add_song_to_aggregates(self, song: Song):
        album_key = self._album_key(song)
        if album_key not in self._album_map:
            album = Album(
                title=song.props.album,
                artist=song.props.album_artist,
                year=song.props.year,
                thumbnail=song.props.thumbnail,
                songs=Gio.ListStore.new(Song),
            )
            self._album_map[album_key] = album
            self._albums.append(album)
        else:
            album = self._album_map[album_key]

        album.props.songs.append(song)
        self._refresh_album(album)

        artist_key = song.props.artist
        if artist_key not in self._artist_map:
            artist = Artist(name=artist_key)
            self._artist_map[artist_key] = artist
            self._artists.append(artist)
        self._refresh_or_remove_artist(artist_key)

        if song.props.album_artist != artist_key:
            self._refresh_or_remove_artist(song.props.album_artist)

    def _remove_song_from_aggregates(self, song: Song):
        album_key = self._album_key(song)
        album = self._album_map.get(album_key)
        if album and album.props.songs:
            song_index = self._find_song_index_in_model(album.props.songs, song.props.url)
            if song_index >= 0:
                album.props.songs.remove(song_index)

            if album.props.songs.get_n_items() == 0:
                album_index = self._find_model_index(self._albums, album)
                if album_index >= 0:
                    self._albums.remove(album_index)
                del self._album_map[album_key]
            else:
                self._refresh_album(album)

        self._refresh_or_remove_artist(song.props.artist)
        if song.props.album_artist != song.props.artist:
            self._refresh_or_remove_artist(song.props.album_artist)

    def _album_key(self, song: Song) -> str:
        return f"{song.props.album}|{song.props.album_artist}"

    def _refresh_album(self, album: Album):
        songs = album.props.songs
        if songs is None:
            return

        album.props.song_count = songs.get_n_items()
        album.props.duration = 0
        album.props.thumbnail = ""
        album.props.year = ""

        for index in range(songs.get_n_items()):
            song = songs.get_item(index)
            album.props.duration += song.props.duration
            if not album.props.thumbnail and song.props.thumbnail:
                album.props.thumbnail = song.props.thumbnail
            if not album.props.year and song.props.year:
                album.props.year = song.props.year

    def _refresh_or_remove_artist(self, artist_key: str):
        artist = self._artist_map.get(artist_key)
        if artist is None:
            return

        song_count = 0
        artist_albums = set()
        for index in range(self._songs.get_n_items()):
            song = self._songs.get_item(index)
            if song.props.artist == artist_key:
                song_count += 1
            if song.props.artist == artist_key or song.props.album_artist == artist_key:
                artist_albums.add(song.props.album)

        if song_count == 0:
            artist_index = self._find_model_index(self._artists, artist)
            if artist_index >= 0:
                self._artists.remove(artist_index)
            del self._artist_map[artist_key]
            return

        artist.props.song_count = song_count
        artist.props.album_count = len(artist_albums)

    def _find_model_index(self, model: Gio.ListStore, item) -> int:
        for index in range(model.get_n_items()):
            if model.get_item(index) is item:
                return index

        return -1

    def _find_song_index_in_model(self, model: Gio.ListStore, url: str) -> int:
        for index in range(model.get_n_items()):
            song = model.get_item(index)
            if song.props.url == url:
                return index

        return -1

    def _rebuild_aggregates(self):
        self._albums.remove_all()
        self._artists.remove_all()
        self._album_map.clear()
        self._artist_map.clear()

        for song in self.get_all_songs():
            self._add_song_to_aggregates(song)

    def _find_song_index_by_url(self, url: str) -> int:
        for index in range(self._songs.get_n_items()):
            song = self._songs.get_item(index)
            if song.props.url == url:
                return index

        return -1

    def _song_signature(self, song: Song):
        return (
            song.props.title,
            song.props.artist,
            song.props.album,
            song.props.album_artist,
            song.props.duration,
            song.props.track_number,
            song.props.disc_number,
            song.props.year,
            song.props.genre,
            song.props.url,
            song.props.thumbnail or "",
        )

    def get_songs_for_album(self, album_title: str, album_artist: str) -> Gio.ListStore:
        """Get all songs for a specific album."""
        key = f"{album_title}|{album_artist}"
        album = self._album_map.get(key)
        if album:
            return album.props.songs
        return Gio.ListStore.new(Song)

    def get_albums_for_artist(self, artist_name: str) -> list[Album]:
        """Get all albums for a specific artist."""
        albums = []
        for i in range(self._albums.get_n_items()):
            album = self._albums.get_item(i)
            if album.props.artist == artist_name:
                albums.append(album)
                continue

            songs = album.props.songs
            if songs is None:
                continue

            for song_index in range(songs.get_n_items()):
                song = songs.get_item(song_index)
                if song.props.artist == artist_name:
                    albums.append(album)
                    break

        return albums

    def search(self, query: str) -> Gio.ListStore:
        """Search songs by title, artist, or album."""
        results = Gio.ListStore.new(Song)
        query_normalized = self._normalize_search_text(query)
        if not query_normalized:
            return results

        matches = []

        for i in range(self._songs.get_n_items()):
            song = self._songs.get_item(i)
            rank = self._search_rank(song, query_normalized)
            if rank is not None:
                matches.append((rank, self._song_sort_key(song), song))

        matches.sort(key=lambda item: (item[0], item[1]))
        for _rank, _sort_key, song in matches:
            results.append(song)

        return results

    def search_albums(self, query: str) -> list[Album]:
        query_normalized = self._normalize_search_text(query)
        if not query_normalized:
            return []

        matches = []
        for i in range(self._albums.get_n_items()):
            album = self._albums.get_item(i)
            rank = self._search_album_rank(album, query_normalized)
            if rank is not None:
                matches.append((
                    rank,
                    (album.props.artist.lower(), album.props.year, album.props.title.lower()),
                    album,
                ))

        matches.sort(key=lambda item: (item[0], item[1]))
        return [album for _rank, _sort_key, album in matches]

    def search_artists(self, query: str) -> list[Artist]:
        query_normalized = self._normalize_search_text(query)
        if not query_normalized:
            return []

        matches = []
        for i in range(self._artists.get_n_items()):
            artist = self._artists.get_item(i)
            field = self._normalize_search_text(artist.props.name)
            if field == query_normalized:
                matches.append((0, artist.props.name.lower(), artist))
            elif field.startswith(query_normalized):
                matches.append((10, artist.props.name.lower(), artist))
            elif query_normalized in field:
                matches.append((20, artist.props.name.lower(), artist))

        matches.sort(key=lambda item: (item[0], item[1]))
        return [artist for _rank, _sort_key, artist in matches]

    def _normalize_search_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.casefold())
        return "".join(
            char for char in normalized
            if not unicodedata.combining(char)
        ).strip()

    def _search_rank(self, song: Song, query: str) -> int | None:
        fields = (
            song.props.title,
            song.props.artist,
            song.props.album,
            song.props.album_artist,
            song.props.genre,
            song.props.year,
        )
        normalized_fields = [
            self._normalize_search_text(field)
            for field in fields
            if field
        ]

        for index, field in enumerate(normalized_fields):
            if field == query:
                return index

        for index, field in enumerate(normalized_fields):
            if field.startswith(query):
                return 10 + index

        for index, field in enumerate(normalized_fields):
            if query in field:
                return 20 + index

        return None

    def _search_album_rank(self, album: Album, query: str) -> int | None:
        fields = (
            album.props.title,
            album.props.artist,
            album.props.year,
        )
        normalized_fields = [
            self._normalize_search_text(field)
            for field in fields
            if field
        ]

        for index, field in enumerate(normalized_fields):
            if field == query:
                return index

        for index, field in enumerate(normalized_fields):
            if field.startswith(query):
                return 10 + index

        for index, field in enumerate(normalized_fields):
            if query in field:
                return 20 + index

        return None
