import json
from pathlib import Path
import tempfile
import unittest

from gi.repository import Gio, GLib

from soundsgood.catalog.playlist_storage import (
    FORMAT_VERSION,
    PlaylistStorageError,
    export_m3u8,
    load_document,
    normalize_document,
    save_document,
)
from soundsgood.models import Song
from soundsgood.playlists import PlaylistManager


class FakeLibrary:
    def __init__(self, songs):
        self._songs = songs

    def get_all_songs(self):
        return list(self._songs)

    def create_songs_for_file(self, _file):
        return list(self._songs)


class PlaylistStorageTest(unittest.TestCase):
    def test_document_round_trip_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            document = {
                "version": FORMAT_VERSION,
                "playlists": [
                    {
                        "id": "playlist-1",
                        "name": "Road trip",
                        "updated_at": "2026-07-19T00:00:00+00:00",
                        "entries": [
                            {
                                "id": "entry-1",
                                "url": "file:///music/Música.flac",
                                "title": "Música",
                                "artist": "Artist",
                                "album": "Album",
                                "duration": 120,
                                "thumbnail": "",
                            }
                        ],
                    }
                ],
            }

            save_document(path, document)

            self.assertEqual(load_document(path), document)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_invalid_or_duplicate_records_are_rejected(self):
        with self.assertRaises(PlaylistStorageError):
            normalize_document({"version": FORMAT_VERSION + 1, "playlists": []})
        with self.assertRaises(PlaylistStorageError):
            normalize_document(
                {
                    "version": FORMAT_VERSION,
                    "playlists": [
                        {"id": "one", "name": "Mix", "entries": []},
                        {"id": "two", "name": "mix", "entries": []},
                    ],
                }
            )

    def test_export_uses_utf8_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "exports" / "mix.m3u8"
            song = root / "Música.flac"
            entries = [
                {
                    "id": "entry-1",
                    "url": song.resolve().as_uri(),
                    "title": "Música",
                    "artist": "Artist",
                    "album": "Album",
                    "duration": 65,
                    "thumbnail": "",
                }
            ]

            export_m3u8(output, entries)

            text = output.read_text(encoding="utf-8")
            self.assertIn("#EXTM3U", text)
            self.assertIn("#EXTINF:65,Artist - Música", text)
            self.assertIn("../Música.flac", text)


class PlaylistManagerTest(unittest.TestCase):
    def test_crud_reorder_resolve_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            first = Song(
                title="First",
                artist="Artist",
                album="Album",
                duration=60,
                url=(Path(directory) / "first.flac").as_uri(),
            )
            second = Song(
                title="Second",
                artist="Artist",
                album="Album",
                duration=70,
                url=(Path(directory) / "second.flac").as_uri(),
            )
            manager = PlaylistManager(path=path, load_async=False)

            playlist = manager.create("Favorites", [first, second])
            self.assertEqual(playlist.props.entry_count, 2)
            self.assertEqual(manager.add_songs(playlist, [first]), 0)
            manager.move_entry(playlist, 1, 0)
            self.assertEqual(
                playlist.props.entries.get_item(0).props.title,
                "Second",
            )
            manager.rename(playlist, "Daily mix")
            self.assertEqual(
                [song.props.title for song in manager.resolved_songs(playlist, FakeLibrary([first]))],
                ["Second", "First"],
            )
            manager.remove_entry(playlist, 1)
            manager.flush()
            manager.shutdown()

            reloaded = PlaylistManager(path=path, load_async=False)
            restored = reloaded.props.playlists.get_item(0)
            self.assertEqual(restored.props.name, "Daily mix")
            self.assertEqual(restored.props.entry_count, 1)
            self.assertEqual(restored.props.entries.get_item(0).props.title, "Second")
            reloaded.delete(restored)
            reloaded.flush()
            reloaded.shutdown()
            self.assertEqual(json.loads(path.read_text())["playlists"], [])

    def test_names_are_unique_and_only_local_songs_are_added(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = PlaylistManager(
                path=Path(directory) / "playlists.json",
                load_async=False,
            )
            first = manager.create("Mix")
            second = manager.create("Mix")
            self.assertEqual(first.props.name, "Mix")
            self.assertEqual(second.props.name, "Mix 2")
            with self.assertRaises(PlaylistStorageError):
                manager.rename(second, "mix")
            self.assertEqual(
                manager.add_songs(
                    first,
                    [Song(title="Remote", url="https://example.com/song.mp3")],
                ),
                0,
            )
            manager.shutdown()

    def test_immediate_shutdown_does_not_replace_existing_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            original = {
                "version": FORMAT_VERSION,
                "playlists": [
                    {
                        "id": "keep-me",
                        "name": "Keep me",
                        "updated_at": "",
                        "entries": [],
                    }
                ],
            }
            save_document(path, original)

            manager = PlaylistManager(path=path, load_async=True)
            manager.shutdown()

            self.assertEqual(load_document(path), original)

    def test_unavailable_snapshot_is_skipped_without_changing_saved_order(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = PlaylistManager(
                path=Path(directory) / "playlists.json",
                load_async=False,
            )
            playlist = manager.create(
                "Missing files",
                [
                    Song(title="Missing", url="file:///tmp/missing-playlist.flac"),
                    Song(title="Known", url="file:///tmp/known-playlist.flac"),
                ],
            )
            playlist.props.entries.get_item(0).props.available = False
            known = Song(title="Known", url="file:///tmp/known-playlist.flac")

            resolved = manager.resolved_songs(playlist, FakeLibrary([known]))

            self.assertEqual([song.props.title for song in resolved], ["Known"])
            self.assertEqual(playlist.props.entries.get_item(0).props.title, "Missing")
            self.assertEqual(playlist.props.entry_count, 2)
            manager.shutdown()

    def test_async_import_creates_named_persistent_playlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = PlaylistManager(
                path=root / "playlists.json",
                load_async=False,
            )
            imported_song = Song(
                title="Imported",
                url=(root / "imported.flac").as_uri(),
            )
            source = Gio.File.new_for_path(str(root / "Road Trip.m3u8"))
            result = []
            loop = GLib.MainLoop()

            def completed(playlist, error):
                result.append((playlist, error))
                loop.quit()

            manager.import_async(source, FakeLibrary([imported_song]), completed)
            loop.run()

            playlist, error = result[0]
            self.assertIsNone(error)
            self.assertEqual(playlist.props.name, "Road Trip")
            self.assertEqual(playlist.props.entry_count, 1)
            manager.flush()
            manager.shutdown()
            self.assertEqual(load_document(root / "playlists.json")["playlists"][0]["name"], "Road Trip")

    def test_unreadable_document_is_not_erased_on_clean_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertLogs("soundsgood.playlists", level="WARNING"):
                manager = PlaylistManager(path=path, load_async=True)
                loop = GLib.MainLoop()
                manager.connect("loaded", lambda *_args: loop.quit())
                loop.run()

            manager.shutdown()

            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
