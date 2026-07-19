import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
    @staticmethod
    def _songs(root, count, prefix="song"):
        return [
            Song(
                title=f"Song {index}",
                artist="Stress artist",
                album="Stress album",
                duration=index,
                url=(root / f"{prefix}-{index}.flac").as_uri(),
            )
            for index in range(count)
        ]

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

    def test_rapid_mutations_are_coalesced_and_survive_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "playlists.json"
            songs = self._songs(root, 100)
            manager = PlaylistManager(path=path, load_async=False)

            for index in range(50):
                manager.create(f"Stress {index:02d}", songs)

            self.assertNotEqual(manager._save_source_id, 0)
            manager.flush()
            self.assertEqual(manager._save_source_id, 0)
            manager.shutdown()

            for cycle in range(3):
                manager = PlaylistManager(path=path, load_async=False)
                self.assertEqual(manager.props.playlists.get_n_items(), 50)
                for index in range(manager.props.playlists.get_n_items()):
                    playlist = manager.props.playlists.get_item(index)
                    self.assertEqual(playlist.props.entry_count, 100)
                    manager.move_entry(playlist, 99, 0)
                manager.flush()
                manager.shutdown()

            restored = load_document(path)
            self.assertEqual(len(restored["playlists"]), 50)
            self.assertTrue(
                all(len(playlist["entries"]) == 100 for playlist in restored["playlists"])
            )
            self.assertEqual(
                restored["playlists"][0]["entries"][0]["title"],
                "Song 97",
            )

    def test_limits_are_rejected_before_partial_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = PlaylistManager(path=root / "playlists.json", load_async=False)
            playlist = manager.create("Bounded", self._songs(root, 2))

            with patch("soundsgood.playlists.MAX_ENTRIES", 3):
                with self.assertRaises(PlaylistStorageError):
                    manager.add_songs(
                        playlist,
                        self._songs(root, 2, prefix="additional"),
                    )
            self.assertEqual(playlist.props.entry_count, 2)

            with patch("soundsgood.playlists.MAX_PLAYLISTS", 1):
                with self.assertRaises(PlaylistStorageError):
                    manager.create("Too many")
            self.assertEqual(manager.props.playlists.get_n_items(), 1)
            manager.shutdown()

    def test_failed_flush_preserves_last_document_and_can_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            manager = PlaylistManager(path=path, load_async=False)
            playlist = manager.create("Before failure")
            manager.flush()
            manager.rename(playlist, "After recovery")

            with patch(
                "soundsgood.playlists.save_document",
                side_effect=PlaylistStorageError("simulated full disk"),
            ):
                with self.assertRaises(PlaylistStorageError):
                    manager.flush()

            self.assertEqual(load_document(path)["playlists"][0]["name"], "Before failure")
            self.assertTrue(manager._dirty)
            manager.flush()
            manager.shutdown()
            self.assertEqual(load_document(path)["playlists"][0]["name"], "After recovery")

    def test_debounced_save_persists_automatically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            manager = PlaylistManager(path=path, load_async=False)
            manager.create("Automatic save")
            loop = GLib.MainLoop()
            timed_out = []

            def poll_saved():
                if path.exists() and load_document(path)["playlists"]:
                    loop.quit()
                    return GLib.SOURCE_REMOVE
                return GLib.SOURCE_CONTINUE

            def timeout():
                timed_out.append(True)
                loop.quit()
                return GLib.SOURCE_REMOVE

            GLib.timeout_add(20, poll_saved)
            timeout_id = GLib.timeout_add(2_000, timeout)
            loop.run()
            if not timed_out:
                GLib.source_remove(timeout_id)

            self.assertFalse(timed_out)
            self.assertEqual(load_document(path)["playlists"][0]["name"], "Automatic save")
            manager.shutdown()

    def test_debounced_save_error_is_reported_and_remains_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "playlists.json"
            manager = PlaylistManager(path=path, load_async=False)
            errors = []
            loop = GLib.MainLoop()
            manager.connect(
                "error",
                lambda _manager, message: (errors.append(message), loop.quit()),
            )

            with self.assertLogs("soundsgood.playlists", level="ERROR") as logs:
                with patch(
                    "soundsgood.playlists.save_document",
                    side_effect=PlaylistStorageError("simulated full disk"),
                ):
                    manager.create("Retry later")
                    timeout_id = GLib.timeout_add(2_000, lambda: loop.quit())
                    loop.run()
                    GLib.source_remove(timeout_id)

            self.assertEqual(errors, ["simulated full disk"])
            self.assertIn("simulated full disk", "\n".join(logs.output))
            self.assertTrue(manager._dirty)
            manager.flush()
            manager.shutdown()
            self.assertEqual(load_document(path)["playlists"][0]["name"], "Retry later")


if __name__ == "__main__":
    unittest.main()
