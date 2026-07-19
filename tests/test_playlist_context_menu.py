import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from gi.repository import Gio, GLib

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
        self.menu._app = SimpleNamespace(
            props=SimpleNamespace(window=None),
        )

    def tearDown(self):
        self.manager.shutdown()
        self._temporary_directory.cleanup()

    def test_menu_model_exposes_current_playlists_as_targeted_actions(self):
        model = self.menu._build_menu_model()
        self.assertEqual(model.get_n_items(), 1)
        submenu = model.get_item_link(0, Gio.MENU_LINK_SUBMENU)
        self.assertIsNotNone(submenu)

        label = submenu.get_item_attribute_value(
            0,
            Gio.MENU_ATTRIBUTE_LABEL,
            GLib.VariantType.new("s"),
        )
        action = submenu.get_item_attribute_value(
            0,
            Gio.MENU_ATTRIBUTE_ACTION,
            GLib.VariantType.new("s"),
        )
        target = submenu.get_item_attribute_value(
            0,
            Gio.MENU_ATTRIBUTE_TARGET,
            GLib.VariantType.new("s"),
        )
        self.assertEqual(label.get_string(), "Favorites")
        self.assertEqual(action.get_string(), "playlist-context.add")
        self.assertEqual(target.get_string(), self.playlist.props.identifier)

        self.manager.rename(self.playlist, "Renamed")
        refreshed = self.menu._build_menu_model().get_item_link(
            0,
            Gio.MENU_LINK_SUBMENU,
        )
        refreshed_label = refreshed.get_item_attribute_value(
            0,
            Gio.MENU_ATTRIBUTE_LABEL,
            GLib.VariantType.new("s"),
        )
        self.assertEqual(refreshed_label.get_string(), "Renamed")

    def test_targeted_action_adds_snapshot_to_selected_playlist(self):
        self.menu._add_to_playlist(
            None,
            GLib.Variant("s", self.playlist.props.identifier),
        )
        self.assertEqual(self.playlist.props.entry_count, 1)
        self.assertEqual(
            self.playlist.props.entries.get_item(0).props.url,
            self.song.props.url,
        )


if __name__ == "__main__":
    unittest.main()
