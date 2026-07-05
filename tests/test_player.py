import unittest

import gi

gi.require_version("Gst", "1.0")

from gi.repository import Gst

from soundsgood.models import Song
from soundsgood.player import Player


Gst.init(None)


class FakeSettings:
    def __init__(self):
        self.values = {
            "volume": 1.0,
            "mute": False,
            "repeat": 0,
        }

    def get_double(self, key):
        return self.values[key]

    def set_double(self, key, value):
        self.values[key] = value

    def get_boolean(self, key):
        return self.values[key]

    def set_boolean(self, key, value):
        self.values[key] = value

    def get_enum(self, key):
        return self.values[key]

    def set_enum(self, key, value):
        self.values[key] = value


class FakeProps:
    settings = FakeSettings()


class FakeApplication:
    props = FakeProps()


class PlayerTest(unittest.TestCase):
    def setUp(self):
        self.player = Player(FakeApplication())
        self.player._load_song = lambda _song: True

    def tearDown(self):
        self.player.stop(clear_current=True)

    def test_play_song_replaces_playlist_and_sets_index(self):
        first = Song(title="One", url="file:///tmp/one.mp3")
        second = Song(title="Two", url="file:///tmp/two.mp3")

        self.player.play_song(second, [first, second])

        self.assertEqual(self.player.props.current_song, second)
        self.assertEqual(self.player.get_playlist(), [first, second])
        self.assertEqual(self.player.get_playlist_index(), 1)

    def test_play_playlist_index_changes_current_song(self):
        first = Song(title="One", url="file:///tmp/one.mp3")
        second = Song(title="Two", url="file:///tmp/two.mp3")
        self.player.play_song(first, [first, second])

        self.player.play_playlist_index(1)

        self.assertEqual(self.player.props.current_song, second)
        self.assertEqual(self.player.get_playlist_index(), 1)

    def test_clear_playlist_stops_and_clears_current_song(self):
        song = Song(title="One", url="file:///tmp/one.mp3")
        self.player.play_song(song, [song])

        self.player.clear_playlist()

        self.assertEqual(self.player.get_playlist(), [])
        self.assertIsNone(self.player.props.current_song)

    def test_remove_playlist_item_before_current_adjusts_index(self):
        first = Song(title="One", url="file:///tmp/one.mp3")
        second = Song(title="Two", url="file:///tmp/two.mp3")
        third = Song(title="Three", url="file:///tmp/three.mp3")
        self.player.play_song(third, [first, second, third])

        self.player.remove_playlist_index(0)

        self.assertEqual(self.player.get_playlist(), [second, third])
        self.assertEqual(self.player.props.current_song, third)
        self.assertEqual(self.player.get_playlist_index(), 1)

    def test_remove_current_playlist_item_plays_next_available(self):
        first = Song(title="One", url="file:///tmp/one.mp3")
        second = Song(title="Two", url="file:///tmp/two.mp3")
        third = Song(title="Three", url="file:///tmp/three.mp3")
        self.player.play_song(second, [first, second, third])

        self.player.remove_playlist_index(1)

        self.assertEqual(self.player.get_playlist(), [first, third])
        self.assertEqual(self.player.props.current_song, third)
        self.assertEqual(self.player.get_playlist_index(), 1)

    def test_remove_last_playlist_item_clears_current_song(self):
        song = Song(title="One", url="file:///tmp/one.mp3")
        self.player.play_song(song, [song])

        self.player.remove_playlist_index(0)

        self.assertEqual(self.player.get_playlist(), [])
        self.assertIsNone(self.player.props.current_song)


if __name__ == "__main__":
    unittest.main()
