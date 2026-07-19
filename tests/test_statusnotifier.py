import unittest
from types import SimpleNamespace

from soundsgood.models import PlayState, Song
from soundsgood.statusnotifier import StatusNotifierService


class FakePlayer:
    def __init__(self):
        self.props = SimpleNamespace(
            current_song=None,
            play_state=int(PlayState.STOPPED),
            volume=0.5,
        )
        self.calls = []

    def play_pause(self):
        self.calls.append("play_pause")

    def previous(self):
        self.calls.append("previous")

    def next(self):
        self.calls.append("next")


class FakeApplication:
    def __init__(self):
        self.props = SimpleNamespace(player=FakePlayer())
        self.calls = []

    def get_application_id(self):
        return "io.github.n1ghthill.soundsgood"

    def show_main_window(self):
        self.calls.append("show")

    def quit_application(self):
        self.calls.append("quit")


def make_service():
    app = FakeApplication()
    service = StatusNotifierService.__new__(StatusNotifierService)
    service._app = app
    service._player = app.props.player
    service._connection = None
    service._registration_ids = []
    service._player_handlers = []
    return service, app


class StatusNotifierServiceTest(unittest.TestCase):
    def test_item_properties_follow_current_song(self):
        service, app = make_service()
        app.props.player.props.current_song = Song(title="Track", artist="Artist")

        title = service._get_item_property(None, None, None, None, "Title")
        tooltip = service._get_item_property(None, None, None, None, "ToolTip")

        self.assertEqual(title.unpack(), "Track")
        self.assertEqual(tooltip.unpack()[2:], ("Track", "Artist"))

    def test_menu_layout_contains_open_transport_and_quit(self):
        service, _app = make_service()
        layout = service._menu_layout()

        self.assertEqual(layout[0], 0)
        self.assertEqual(
            [child.unpack()[0] for child in layout[2]],
            [1, 2, 3, 4, 5, 6],
        )

    def test_menu_actions_delegate_without_owning_player_state(self):
        service, app = make_service()

        for item_id in (
            service.OPEN,
            service.PLAY_PAUSE,
            service.PREVIOUS,
            service.NEXT,
            service.QUIT,
        ):
            service._activate_menu_item(item_id)

        self.assertEqual(app.calls, ["show", "quit"])
        self.assertEqual(
            app.props.player.calls,
            ["play_pause", "previous", "next"],
        )


if __name__ == "__main__":
    unittest.main()
