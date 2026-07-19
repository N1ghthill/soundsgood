import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from soundsgood.models import Song
from soundsgood.playlists import PlaylistManager
from soundsgood.widgets.playlistcontextmenu import PlaylistContextMenu


class PlaylistContextMenuTest(unittest.TestCase):
    def setUp(self):
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.manager = PlaylistManager(
            path=Path(self._temporary_directory.name) / "playlists.json",
            load_async=False,
        )
        self.song = Song(title="Context song", url="file:///tmp/context.wav")
        self.playlist = self.manager.create("Favorites")
        self.menu = PlaylistContextMenu.__new__(PlaylistContextMenu)
        self.menu._manager = self.manager
        self.menu._submenu_label = "Add to Playlist"
        self.menu._description_provider = None
        self.menu._songs = [self.song]
        self.menu._popover = None
        self.menu._app = SimpleNamespace(
            props=SimpleNamespace(window=None),
        )

    def tearDown(self):
        self.manager.shutdown()
        self._temporary_directory.cleanup()

    def test_destination_lookup_uses_stable_playlist_identifier(self):
        self.assertIs(
            self.menu._find_playlist(self.playlist.props.identifier),
            self.playlist,
        )

        self.manager.rename(self.playlist, "Renamed")
        self.assertEqual(
            self.menu._find_playlist(self.playlist.props.identifier).props.name,
            "Renamed",
        )

    def test_targeted_action_adds_snapshot_to_selected_playlist(self):
        self.menu._activate_playlist(self.playlist)
        self.assertEqual(self.playlist.props.entry_count, 1)
        self.assertEqual(
            self.playlist.props.entries.get_item(0).props.url,
            self.song.props.url,
        )


if __name__ == "__main__":
    unittest.main()
