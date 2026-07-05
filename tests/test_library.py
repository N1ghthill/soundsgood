import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from soundsgood.library import Library
from soundsgood.models import LibraryState, Song


class FakeSettings:
    def get_string(self, _key):
        return ""


class FakeProps:
    settings = FakeSettings()


class FakeApplication:
    props = FakeProps()


class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.library = Library(FakeApplication())

    def test_search_normalizes_accents(self):
        self.library._add_song(
            Song(
                title="Musica Boa",
                artist="Arvore",
                album="Album Azul",
                album_artist="Arvore",
                url="file:///tmp/one.mp3",
            )
        )

        results = self.library.search("música")

        self.assertEqual(results.get_n_items(), 1)
        self.assertEqual(results.get_item(0).props.title, "Musica Boa")

    def test_search_albums_and_artists(self):
        self.library._add_song(
            Song(
                title="Track",
                artist="Artist",
                album="The Album",
                album_artist="Artist",
                url="file:///tmp/track.mp3",
            )
        )

        self.assertEqual(
            [album.props.title for album in self.library.search_albums("album")],
            ["The Album"],
        )
        self.assertEqual(
            [artist.props.name for artist in self.library.search_artists("artist")],
            ["Artist"],
        )

    def test_scan_snapshot_applies_diff_by_uri(self):
        first = Song(
            title="One",
            artist="Artist",
            album="Album",
            album_artist="Artist",
            url="file:///tmp/one.mp3",
        )
        second = Song(
            title="Two",
            artist="Artist",
            album="Album",
            album_artist="Artist",
            url="file:///tmp/two.mp3",
        )
        changed = Song(
            title="Two Changed",
            artist="Artist",
            album="Album",
            album_artist="Artist",
            url="file:///tmp/two.mp3",
        )

        self.library._apply_scan_results([first, second])
        self.library._apply_scan_results([changed])

        self.assertEqual(
            [song.props.title for song in self.library.get_all_songs()],
            ["Two Changed"],
        )
        self.assertEqual(self.library.props.albums.get_n_items(), 1)
        self.assertEqual(self.library.props.albums.get_item(0).props.song_count, 1)

    def test_scan_snapshot_updates_album_aggregates_incrementally(self):
        first = Song(
            title="One",
            artist="Artist",
            album="First Album",
            album_artist="Artist",
            duration=10,
            url="file:///tmp/one.mp3",
            thumbnail="/tmp/one.jpg",
        )
        second = Song(
            title="Two",
            artist="Artist",
            album="First Album",
            album_artist="Artist",
            duration=20,
            url="file:///tmp/two.mp3",
        )
        moved = Song(
            title="Two",
            artist="Artist",
            album="Second Album",
            album_artist="Artist",
            duration=30,
            url="file:///tmp/two.mp3",
            thumbnail="/tmp/two.jpg",
        )
        self.library._rebuild_aggregates = lambda: self.fail("full aggregate rebuild was used")

        self.library._apply_scan_results([first, second])
        self.library._apply_scan_results([moved])

        self.assertEqual(
            [album.props.title for album in self._albums()],
            ["Second Album"],
        )
        album = self.library.props.albums.get_item(0)
        self.assertEqual(album.props.song_count, 1)
        self.assertEqual(album.props.duration, 30)
        self.assertEqual(album.props.thumbnail, "/tmp/two.jpg")

    def test_scan_snapshot_updates_artist_aggregates_incrementally(self):
        first = Song(
            title="One",
            artist="First Artist",
            album="Album",
            album_artist="First Artist",
            url="file:///tmp/one.mp3",
        )
        changed = Song(
            title="One",
            artist="Second Artist",
            album="Album",
            album_artist="Second Artist",
            url="file:///tmp/one.mp3",
        )
        self.library._rebuild_aggregates = lambda: self.fail("full aggregate rebuild was used")

        self.library._apply_scan_results([first])
        self.library._apply_scan_results([changed])

        self.assertEqual(
            [artist.props.name for artist in self._artists()],
            ["Second Artist"],
        )
        artist = self.library.props.artists.get_item(0)
        self.assertEqual(artist.props.song_count, 1)
        self.assertEqual(artist.props.album_count, 1)

    def test_cache_round_trip_keeps_song_metadata(self):
        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "library.json"
            self.library._cache_path = lambda: cache_path
            song = Song(
                title="Música Boa",
                artist="Árvore",
                album="Álbum Azul",
                album_artist="Árvore",
                duration=123,
                track_number=7,
                disc_number=2,
                year="2025",
                genre="MPB",
                url="file:///tmp/musica.mp3",
                thumbnail="/tmp/cover.jpg",
            )
            record = self.library._record_from_song(
                song,
                "/tmp/musica.mp3",
                {"mtime_ns": 10, "size": 20},
            )

            self.library._save_cache("/tmp/music", [record])
            cache = self.library._load_cache("/tmp/music")
            cached_song = self.library._song_from_record(cache["songs"][0])

            self.assertEqual(cache["directory"], "/tmp/music")
            self.assertEqual(cached_song.props.title, "Música Boa")
            self.assertEqual(cached_song.props.artist, "Árvore")
            self.assertEqual(cached_song.props.track_number, 7)
            self.assertEqual(cached_song.props.thumbnail, "/tmp/cover.jpg")

    def test_cache_ignores_other_library_directory(self):
        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "library.json"
            cache_path.write_text(
                json.dumps({"version": 1, "directory": "/tmp/other", "songs": []}),
                encoding="utf-8",
            )
            self.library._cache_path = lambda: cache_path

            self.assertEqual(self.library._load_cache("/tmp/music"), {})

    def test_cache_ignores_invalid_json(self):
        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "library.json"
            cache_path.write_text("{", encoding="utf-8")
            self.library._cache_path = lambda: cache_path

            self.assertEqual(self.library._load_cache("/tmp/music"), {})

    def test_record_matches_file_uses_mtime_and_size(self):
        record = {"mtime_ns": 10, "size": 20}

        self.assertTrue(self.library._record_matches_file(record, {"mtime_ns": 10, "size": 20}))
        self.assertFalse(self.library._record_matches_file(record, {"mtime_ns": 11, "size": 20}))
        self.assertFalse(self.library._record_matches_file(record, {"mtime_ns": 10, "size": 21}))

    def test_scan_invalid_directory_sets_error_state(self):
        errors = []
        self.library.connect("scan-error", lambda _library, message: errors.append(message))

        self.library.scan("/tmp/soundsgood-does-not-exist")

        self.assertEqual(self.library.props.scan_state, int(LibraryState.ERROR))
        self.assertEqual(self.library.props.status_message, "Music folder not found")
        self.assertEqual(errors, ["Music folder not found"])

    def test_scan_results_empty_sets_empty_state(self):
        self.library._apply_scan_results([])

        self.assertEqual(self.library.props.scan_state, int(LibraryState.EMPTY))
        self.assertEqual(self.library.props.status_message, "No music found")
        self.assertFalse(self.library.props.songs_available)

    def test_scan_results_with_songs_sets_ready_state(self):
        self.library._apply_scan_results([
            Song(
                title="One",
                artist="Artist",
                album="Album",
                album_artist="Artist",
                url="file:///tmp/one.mp3",
            )
        ])

        self.assertEqual(self.library.props.scan_state, int(LibraryState.READY))
        self.assertEqual(self.library.props.status_message, "")
        self.assertTrue(self.library.props.songs_available)

    def _albums(self):
        return [
            self.library.props.albums.get_item(index)
            for index in range(self.library.props.albums.get_n_items())
        ]

    def _artists(self):
        return [
            self.library.props.artists.get_item(index)
            for index in range(self.library.props.artists.get_n_items())
        ]


if __name__ == "__main__":
    unittest.main()
