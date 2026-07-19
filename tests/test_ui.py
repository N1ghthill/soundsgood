import unittest

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GLib

from soundsgood.application import SoundsGoodApplication
from soundsgood.models import Song
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

                window._artists_view.set_compact(True)
                self.assertTrue(window._artists_view._split_view.get_collapsed())
                window._artists_view.set_compact(False)
                self.assertFalse(window._artists_view._split_view.get_collapsed())

                item = SongListItem(app.props.player, lambda _song: None, True)
                item.bind(Song(title="Lifecycle", url="file:///tmp/test.wav"))
                self.assertEqual(len(item._player_handlers), 2)
                item.unbind()
                self.assertEqual(item._player_handlers, [])

                player = app.props.player
                player._load_song = lambda _song: True
                first = Song(title="First", url="file:///tmp/first.wav")
                second = Song(title="Second", url="file:///tmp/second.wav")
                player.play_song(first, [first, second])
                queue = window._player_toolbar
                self.assertEqual(queue._queue_model.get_n_items(), 2)
                self.assertEqual(queue._queue_selection.get_selected(), 0)
                queue._on_remove_queue_item(0)
                self.assertEqual(queue._queue_model.get_n_items(), 1)
            except Exception as error:
                failures.append(error)
            finally:
                app.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(100, inspect_window)
        exit_code = app.run([])
        if failures:
            raise failures[0]
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
