import hashlib
import unittest
from types import SimpleNamespace

from gi.repository import GLib

from soundsgood.models import PlayState, RepeatMode, Song
from soundsgood.mpris import MprisService


class FakeParameters:
    def __init__(self, value):
        self._value = value

    def unpack(self):
        return self._value


class FakePlayer:
    def __init__(self):
        self.props = SimpleNamespace(
            current_song=None,
            play_state=int(PlayState.STOPPED),
            repeat_mode=int(RepeatMode.NONE),
            volume=0.5,
            position=0,
            duration=0,
        )
        self.calls = []
        self.playlist = []
        self.playlist_index = -1

    def next(self):
        self.calls.append(("next",))

    def previous(self):
        self.calls.append(("previous",))

    def pause(self):
        self.calls.append(("pause",))

    def play_pause(self):
        self.calls.append(("play_pause",))

    def stop(self, clear_current=False):
        self.calls.append(("stop", clear_current))

    def seek(self, position):
        self.calls.append(("seek", position))
        self.props.position = position

    def get_playlist(self):
        return list(self.playlist)

    def get_playlist_index(self):
        return self.playlist_index


class FakeConnection:
    def __init__(self):
        self.signals = []

    def emit_signal(self, *args):
        self.signals.append(args)


def make_service(player):
    service = MprisService.__new__(MprisService)
    service._player = player
    service._connection = None
    return service


class MprisServiceTest(unittest.TestCase):
    def setUp(self):
        self.player = FakePlayer()
        self.service = make_service(self.player)

    def test_playback_status_follows_player_state(self):
        self.assertEqual(self.service._playback_status(), "Stopped")

        self.player.props.play_state = int(PlayState.PAUSED)
        self.assertEqual(self.service._playback_status(), "Paused")

        self.player.props.play_state = int(PlayState.PLAYING)
        self.assertEqual(self.service._playback_status(), "Playing")

    def test_loop_status_maps_repeat_modes(self):
        self.assertEqual(self.service._loop_status(), "None")

        self.player.props.repeat_mode = int(RepeatMode.SONG)
        self.assertEqual(self.service._loop_status(), "Track")

        self.player.props.repeat_mode = int(RepeatMode.ALL)
        self.assertEqual(self.service._loop_status(), "Playlist")

    def test_set_property_updates_volume_repeat_and_shuffle(self):
        self.assertTrue(
            self.service._set_property(
                None,
                None,
                None,
                "org.mpris.MediaPlayer2.Player",
                "Volume",
                GLib.Variant("d", 1.5),
            )
        )
        self.assertEqual(self.player.props.volume, 1.0)

        self.service._set_property(
            None,
            None,
            None,
            "org.mpris.MediaPlayer2.Player",
            "LoopStatus",
            GLib.Variant("s", "Playlist"),
        )
        self.assertEqual(self.player.props.repeat_mode, int(RepeatMode.ALL))

        self.service._set_property(
            None,
            None,
            None,
            "org.mpris.MediaPlayer2.Player",
            "Shuffle",
            GLib.Variant("b", True),
        )
        self.assertEqual(self.player.props.repeat_mode, int(RepeatMode.SHUFFLE))

    def test_metadata_exports_current_song_fields(self):
        self.player.props.current_song = Song(
            title="Track",
            artist="Artist",
            album="Album",
            album_artist="Album Artist",
            duration=123,
            url="file:///tmp/track.mp3",
            thumbnail="/tmp/cover.jpg",
        )

        metadata = self.service._metadata()

        self.assertEqual(metadata["xesam:title"].unpack(), "Track")
        self.assertEqual(metadata["xesam:artist"].unpack(), ["Artist"])
        self.assertEqual(metadata["xesam:album"].unpack(), "Album")
        self.assertEqual(metadata["xesam:albumArtist"].unpack(), ["Album Artist"])
        self.assertEqual(metadata["mpris:length"].unpack(), 123_000_000)
        self.assertEqual(metadata["xesam:url"].unpack(), "file:///tmp/track.mp3")
        self.assertEqual(metadata["mpris:artUrl"].unpack(), "file:///tmp/cover.jpg")

    def test_transport_capabilities_follow_playlist_and_current_song(self):
        self.assertFalse(self.service._player_property("CanPlay").unpack())
        self.assertFalse(self.service._player_property("CanPause").unpack())
        self.assertFalse(self.service._player_property("CanSeek").unpack())
        self.assertFalse(self.service._player_property("CanGoNext").unpack())
        self.assertFalse(self.service._player_property("CanGoPrevious").unpack())

        first = Song(title="One", duration=100, url="file:///tmp/one.mp3")
        second = Song(title="Two", duration=100, url="file:///tmp/two.mp3")
        self.player.playlist = [first, second]
        self.player.playlist_index = 0

        self.assertTrue(self.service._player_property("CanPlay").unpack())
        self.assertTrue(self.service._player_property("CanGoNext").unpack())
        self.assertFalse(self.service._player_property("CanPause").unpack())
        self.assertFalse(self.service._player_property("CanGoPrevious").unpack())

        self.player.props.current_song = first
        self.player.props.duration = 100
        self.assertTrue(self.service._player_property("CanPause").unpack())
        self.assertTrue(self.service._player_property("CanSeek").unpack())
        self.assertTrue(self.service._player_property("CanGoPrevious").unpack())

        self.player.playlist_index = 1
        self.assertFalse(self.service._player_property("CanGoNext").unpack())

        self.player.props.repeat_mode = int(RepeatMode.ALL)
        self.assertTrue(self.service._player_property("CanGoNext").unpack())

    def test_playlist_changed_emits_transport_capabilities(self):
        connection = FakeConnection()
        self.service._connection = connection

        self.service._on_playlist_changed()

        self.assertEqual(len(connection.signals), 1)
        parameters = connection.signals[0][-1]
        interface_name, changed, invalidated = parameters.unpack()
        self.assertEqual(interface_name, "org.mpris.MediaPlayer2.Player")
        self.assertEqual(invalidated, [])
        self.assertEqual(
            sorted(changed),
            ["CanGoNext", "CanGoPrevious", "CanPause", "CanPlay", "CanSeek"],
        )

    def test_track_id_is_stable_for_same_uri(self):
        uri = "file:///tmp/track.mp3"
        self.player.props.current_song = Song(url=uri)
        digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()

        self.assertEqual(
            self.service._track_id(),
            f"/org/mpris/MediaPlayer2/TrackList/{digest}",
        )
        self.assertEqual(make_service(self.player)._track_id(), self.service._track_id())

    def test_seek_methods_convert_microseconds_to_seconds(self):
        self.player.props.position = 10

        self.service._handle_player_method("Seek", FakeParameters((5_000_000,)))
        self.assertEqual(self.player.calls[-1], ("seek", 15))

        track_id = self.service._track_id()
        self.service._handle_player_method(
            "SetPosition",
            FakeParameters((track_id, 42_000_000)),
        )
        self.assertEqual(self.player.calls[-1], ("seek", 42))

    def test_basic_player_methods_delegate_to_player(self):
        for method in ("Next", "Previous", "Pause", "PlayPause", "Stop"):
            self.service._handle_player_method(method, FakeParameters(()))

        self.assertEqual(
            self.player.calls,
            [
                ("next",),
                ("previous",),
                ("pause",),
                ("play_pause",),
                ("stop", False),
            ],
        )


if __name__ == "__main__":
    unittest.main()
