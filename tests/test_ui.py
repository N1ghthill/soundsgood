import unittest

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, Gio, GLib

from soundsgood.application import SoundsGoodApplication
from soundsgood.models import Album, Artist, Song
from soundsgood.views.albumsview import AlbumTile
from soundsgood.views.artistsview import ArtistListItem
from soundsgood.widgets.songrow import SongListItem


class WindowSmokeTest(unittest.TestCase):
    def test_application_builds_primary_views_at_supported_widths(self):
        if Gdk.Display.get_default() is None:
            self.skipTest("A graphical display is required")

        app = SoundsGoodApplication(
            "io.github.n1ghthill.soundsgood.Test",
            "test",
        )
        app._library.scan = lambda *_args, **_kwargs: None
        failures = []

        def inspect_window():
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
                        window._search_view,
                    )
                }
                self.assertEqual(
                    page_names,
                    {"albums", "artists", "songs", "search"},
                )
                for child in (
                    window._albums_view,
                    window._artists_view,
                    window._songs_view,
                    window._search_view,
                ):
                    self.assertTrue(window._stack.get_page(child).get_icon_name())

                toolbar = window._player_toolbar
                self.assertTrue(toolbar._play_button.has_css_class("primary-play"))
                self.assertTrue(toolbar._previous_button.has_css_class("compact-icon"))
                self.assertTrue(toolbar._queue_button.has_css_class("compact-icon"))
                self.assertTrue(toolbar._progress.has_css_class("player-progress"))
                toolbar.set_compact(True)
                self.assertFalse(toolbar._artist_label.get_visible())
                self.assertFalse(toolbar._time_box.get_visible())
                self.assertEqual(toolbar._cover.get_pixel_size(), 32)
                toolbar.set_compact(False)
                self.assertTrue(toolbar._artist_label.get_visible())
                self.assertTrue(toolbar._time_box.get_visible())
                self.assertEqual(toolbar._cover.get_pixel_size(), 36)

                window._artists_view.set_compact(True)
                self.assertTrue(window._artists_view._split_view.get_collapsed())
                window._artists_view.set_compact(False)
                self.assertFalse(window._artists_view._split_view.get_collapsed())

                item = SongListItem(app.props.player, lambda _song: None, True)
                item.bind(Song(title="Lifecycle", url="file:///tmp/test.wav"))
                self.assertEqual(len(item._player_handlers), 2)
                item.unbind()
                self.assertEqual(item._player_handlers, [])

                album_tile = AlbumTile()
                album = Album(title="Reactive album", song_count=0)
                album_tile.bind(album)
                album.props.song_count = 2
                self.assertEqual(album_tile._count.get_label(), "2 songs")
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
