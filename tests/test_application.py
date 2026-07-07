import unittest

from gi.repository import Gio

from soundsgood.application import SoundsGoodApplication
from soundsgood.models import Song


class FakeLibrary:
    def __init__(self, songs_by_uri):
        self.songs_by_uri = songs_by_uri
        self.scanned = False

    def scan(self):
        self.scanned = True

    def create_songs_for_file(self, file):
        return list(self.songs_by_uri.get(file.get_uri(), []))


class FakePlayer:
    def __init__(self):
        self.played = None

    def play_song(self, song, playlist=None):
        self.played = (song, playlist)


class FakeWindow:
    def __init__(self):
        self.presented = False
        self.messages = []

    def present(self):
        self.presented = True

    def show_message(self, message):
        self.messages.append(message)


class FakeApplication:
    def __init__(self, library):
        self._library = library
        self._player = FakePlayer()
        self._window = FakeWindow()
        self.window_created = False

    def _ensure_window(self):
        self.window_created = True

    def _open_files(self, files):
        SoundsGoodApplication._open_files(self, files)


class ApplicationOpenTest(unittest.TestCase):
    def test_do_open_plays_opened_files_as_temporary_queue(self):
        first = Song(title="First", url="file:///tmp/first.mp3")
        second = Song(title="Second", url="file:///tmp/second.mp3")
        file = Gio.File.new_for_uri("file:///tmp/mix.m3u")
        app = FakeApplication(FakeLibrary({file.get_uri(): [first, second]}))

        SoundsGoodApplication.do_open(app, [file], 1, "")

        self.assertTrue(app.window_created)
        self.assertTrue(app._library.scanned)
        self.assertTrue(app._window.presented)
        self.assertEqual(app._player.played, (first, [first, second]))

    def test_do_open_reports_when_no_playable_files_are_opened(self):
        file = Gio.File.new_for_uri("file:///tmp/notes.txt")
        app = FakeApplication(FakeLibrary({}))

        SoundsGoodApplication.do_open(app, [file], 1, "")

        self.assertIsNone(app._player.played)
        self.assertEqual(app._window.messages, ["No playable audio files"])


if __name__ == "__main__":
    unittest.main()
