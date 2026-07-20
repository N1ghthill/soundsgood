import unittest
import os
import tempfile

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gio, GLib, Gtk

from soundsgood.application import SoundsGoodApplication
from soundsgood.models import Album, Artist, Song
from soundsgood.views.albumsview import AlbumTile
from soundsgood.views.artistsview import ArtistListItem
from soundsgood.widgets.songrow import SongListItem
from soundsgood.widgets.playlistchooser import (
    PlaylistChooserDialog,
    PlaylistSongChooserDialog,
)
from soundsgood.widgets.playlistcontextmenu import PlaylistContextMenu


class WindowSmokeTest(unittest.TestCase):
    def test_application_builds_primary_views_at_supported_widths(self):
        if Gdk.Display.get_default() is None:
            self.skipTest("A graphical display is required")

        with tempfile.TemporaryDirectory() as data_home:
            previous_data_home = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_DATA_HOME"] = data_home
            try:
                self._run_application_smoke()
            finally:
                if previous_data_home is None:
                    os.environ.pop("XDG_DATA_HOME", None)
                else:
                    os.environ["XDG_DATA_HOME"] = previous_data_home

    def _run_application_smoke(self):
        app = SoundsGoodApplication(
            "io.github.n1ghthill.soundsgood.Test",
            "test",
        )
        app._library.scan = lambda *_args, **_kwargs: None
        failures = []

        def inspect_window():
            if not app.props.playlist_manager.props.loaded:
                GLib.timeout_add(20, inspect_window)
                return GLib.SOURCE_REMOVE
            try:
                window = app.props.window
                self.assertIsNotNone(window)
                for width in (360, 600, 900, 1200):
                    window.set_default_size(width, 600)
                    self.assertEqual(window.get_default_size(), (width, 600))

                page_names = {
                    window._stack.get_page(child).get_name()
                    for child in (
                        window._albums_view,
                        window._artists_view,
                        window._songs_view,
                        window._playlists_view,
                        window._search_view,
                    )
                }
                self.assertEqual(
                    page_names,
                    {"albums", "artists", "songs", "playlists", "search"},
                )
                for child in (
                    window._albums_view,
                    window._artists_view,
                    window._songs_view,
                    window._playlists_view,
                ):
                    self.assertTrue(window._stack.get_page(child).get_icon_name())
                self.assertIsNone(
                    window._stack.get_page(window._search_view).get_title()
                )
                window._stack.set_visible_child_name("songs")
                window.show_search()
                self.assertEqual(window._stack.get_visible_child_name(), "search")
                self.assertTrue(
                    window._on_key_pressed(None, Gdk.KEY_Escape, 0, 0)
                )
                self.assertEqual(window._stack.get_visible_child_name(), "songs")
                self.assertFalse(
                    window._on_key_pressed(None, Gdk.KEY_Escape, 0, 0)
                )

                toolbar = window._player_toolbar
                self.assertTrue(toolbar._play_button.has_css_class("primary-play"))
                self.assertTrue(toolbar._previous_button.has_css_class("compact-icon"))
                self.assertTrue(toolbar._queue_button.has_css_class("compact-icon"))
                self.assertTrue(toolbar._progress.has_css_class("player-progress"))
                toolbar.set_compact(True)
                self.assertFalse(toolbar._artist_label.get_visible())
                self.assertFalse(toolbar._time_box.get_visible())
                self.assertEqual(toolbar._cover.get_pixel_size(), 34)
                toolbar.set_compact(False)
                self.assertTrue(toolbar._artist_label.get_visible())
                self.assertTrue(toolbar._time_box.get_visible())
                self.assertEqual(toolbar._cover.get_pixel_size(), 44)

                window._artists_view.set_compact(True)
                self.assertTrue(window._artists_view._split_view.get_collapsed())
                window._artists_view.set_compact(False)
                self.assertFalse(window._artists_view._split_view.get_collapsed())

                window._playlists_view.set_compact(True)
                self.assertTrue(window._playlists_view._split_view.get_collapsed())
                window._playlists_view.set_compact(False)
                self.assertFalse(window._playlists_view._split_view.get_collapsed())

                saved = app.props.playlist_manager.create(
                    "Smoke playlist",
                    [Song(title="Saved", url="file:///tmp/saved.wav")],
                )
                self.assertEqual(saved.props.entry_count, 1)
                window._playlists_view._selection.set_selected(0)
                self.assertIs(window._playlists_view._selected_playlist, saved)

                item = SongListItem(app.props.player, lambda _song: None, True)
                item.bind(Song(title="Lifecycle", url="file:///tmp/test.wav"))
                self.assertEqual(len(item._player_handlers), 2)
                item.unbind()
                self.assertEqual(item._player_handlers, [])

                add_item = SongListItem(
                    app.props.player,
                    lambda _song: None,
                    True,
                    lambda _song: None,
                    app,
                )
                context_song = Song(title="Add action", url="file:///tmp/add.wav")
                add_item.bind(context_song)
                self.assertTrue(add_item._add_button.has_css_class("compact-icon"))
                self.assertIsInstance(
                    add_item._playlist_menu,
                    PlaylistContextMenu,
                )
                add_item._playlist_menu._songs = [context_song]
                context_host = Gtk.Window(application=app)
                context_host.set_child(add_item)
                context_host.present()
                while GLib.MainContext.default().iteration(False):
                    pass
                context_popover = Gtk.Popover()
                context_popover.set_parent(add_item)
                context_popover.set_child(add_item._playlist_menu._build_content())
                context_popover.connect(
                    "closed",
                    add_item._playlist_menu._on_popover_closed,
                )
                add_item._playlist_menu._popover = context_popover
                context_popover.popup()
                while GLib.MainContext.default().iteration(False):
                    pass
                pending = [context_popover]
                destination_button = None
                while pending:
                    candidate = pending.pop()
                    if (
                        isinstance(candidate, Gtk.Button)
                        and candidate.has_css_class("playlist-destination")
                        and candidate._playlist is saved
                    ):
                        destination_button = candidate
                        break
                    child = candidate.get_first_child()
                    while child is not None:
                        pending.append(child)
                        child = child.get_next_sibling()
                self.assertIsNotNone(destination_button)
                self.assertEqual(
                    destination_button._name.get_label(),
                    "Smoke playlist",
                )
                self.assertEqual(destination_button._count.get_label(), "1 song")
                destination_button.emit("clicked")
                while GLib.MainContext.default().iteration(False):
                    pass
                self.assertEqual(saved.props.entry_count, 2)
                context_host.destroy()
                add_item.unbind()

                chooser = PlaylistChooserDialog(
                    app,
                    [Song(title="Chooser", url="file:///tmp/chooser.wav")],
                )
                chooser.present(window)
                self.assertIsNotNone(chooser._list.get_first_child())
                self.assertEqual(len(chooser._manager_handlers), 1)
                chooser.close()

                library_song = Song(
                    title="Café da manhã",
                    artist="Local artist",
                    album="Daily",
                    url="file:///tmp/library-picker.wav",
                )
                app.props.library.props.songs.append(library_song)
                search = window._search_view
                search._run_search("cafe")
                self.assertIsInstance(search._results, Gtk.ListView)
                self.assertEqual(search._model.get_n_items(), 2)
                self.assertEqual(search._model.get_item(0).props.kind, "section")
                self.assertIs(search._model.get_item(1).props.item, library_song)
                song_chooser = PlaylistSongChooserDialog(app, saved)
                song_chooser.present(window)
                song_chooser._search.set_text("cafe")
                self.assertEqual(song_chooser._filtered.get_n_items(), 1)
                song_chooser._selection.select_item(0, False)
                song_chooser._add_selected(None)
                self.assertEqual(saved.props.entry_count, 3)

                replacement = app.props.playlist_manager.create("Keep this one")
                window._playlists_view._selection.set_selected(0)
                window._playlists_view._delete_confirmed(saved)
                self.assertEqual(
                    app.props.playlist_manager.props.playlists.get_n_items(),
                    1,
                )
                self.assertIs(
                    window._playlists_view._selected_playlist,
                    replacement,
                )

                album_tile = AlbumTile(app)
                album = Album(title="Reactive album", song_count=0)
                album_tile.bind(album)
                album.props.song_count = 2
                self.assertEqual(album_tile._count.get_label(), "2 songs")
                self.assertIsInstance(
                    album_tile._playlist_menu,
                    PlaylistContextMenu,
                )
                album_tile.unbind()
                self.assertEqual(album_tile._album_handlers, [])

                detail_songs = Gio.ListStore(item_type=Song)
                detail_songs.append(
                    Song(title="Disc one", disc_number=1, url="file:///tmp/one.wav")
                )
                detail_songs.append(
                    Song(title="Disc two", disc_number=2, url="file:///tmp/two.wav")
                )
                detail_album = Album(
                    title="Virtual detail",
                    artist="Factory",
                    song_count=2,
                    songs=detail_songs,
                )
                album_model = window._albums_view._build_song_model(detail_album)
                self.assertEqual(album_model.get_n_items(), 4)
                self.assertEqual(album_model.get_item(0).props.kind, "heading")
                window._albums_view._show_album(detail_album)
                self.assertEqual(
                    window._albums_view._stack.get_visible_child_name(),
                    "album",
                )
                artist_model = window._artists_view._build_artist_model(
                    [detail_album],
                    "Factory",
                )
                self.assertEqual(artist_model.get_n_items(), 5)
                self.assertEqual(artist_model.get_item(0).props.kind, "album")

                artist_item = ArtistListItem()
                artist = Artist(name="Reactive artist", album_count=0, song_count=0)
                artist_item.bind(artist)
                artist.props.album_count = 1
                artist.props.song_count = 2
                self.assertEqual(artist_item._summary.get_label(), "1 albums, 2 songs")
                artist_item.unbind()
                self.assertEqual(artist_item._artist_handlers, [])

                player = app.props.player
                player._load_song = lambda _song: True
                first = Song(title="First", url="file:///tmp/first.wav")
                second = Song(title="Second", url="file:///tmp/second.wav")
                player.play_song(first, [first, second])
                queue = toolbar
                self.assertEqual(queue._queue_model.get_n_items(), 2)
                self.assertEqual(queue._queue_selection.get_selected(), 0)
                queue._on_remove_queue_item(0)
                self.assertEqual(queue._queue_model.get_n_items(), 1)

                app.props.settings.set_boolean("run-in-background", True)
                app._background._request_background_permission = lambda: None
                self.assertTrue(window._on_close_request())
                self.assertFalse(window.get_visible())
                app.show_main_window()
                self.assertTrue(window.get_visible())
            except Exception as error:
                failures.append(error)
            finally:
                app.quit_application()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(100, inspect_window)
        exit_code = app.run([])
        if failures:
            raise failures[0]
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
