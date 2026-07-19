import unittest
from types import SimpleNamespace

from soundsgood.background import BackgroundController


class FakeSettings:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def get_boolean(self, key):
        if key != "run-in-background":
            raise KeyError(key)
        return self.enabled


class FakeWindow:
    def __init__(self):
        self.visible = True
        self.presented = False

    def set_visible(self, visible):
        self.visible = visible

    def present(self):
        self.visible = True
        self.presented = True


class FakeApplication:
    def __init__(self, enabled=True):
        self.settings = FakeSettings(enabled)
        self.window = FakeWindow()
        self.props = SimpleNamespace(settings=self.settings, window=self.window)
        self.holds = 0
        self.releases = 0
        self.notifications = []
        self.withdrawn = []
        self.quit_called = False

    def hold(self):
        self.holds += 1

    def release(self):
        self.releases += 1

    def send_notification(self, notification_id, notification):
        self.notifications.append((notification_id, notification))

    def withdraw_notification(self, notification_id):
        self.withdrawn.append(notification_id)

    def quit(self):
        self.quit_called = True

    def _ensure_window(self):
        pass


class BackgroundControllerTest(unittest.TestCase):
    def test_close_hides_window_and_holds_application_once(self):
        app = FakeApplication()
        controller = BackgroundController(app)
        controller._request_background_permission = lambda: None

        self.assertTrue(controller.handle_close(app.window))
        self.assertFalse(app.window.visible)
        self.assertEqual(app.holds, 1)
        self.assertEqual(len(app.notifications), 1)

        controller.handle_close(app.window)
        self.assertEqual(app.holds, 1)

    def test_disabled_background_allows_normal_close(self):
        app = FakeApplication(enabled=False)
        controller = BackgroundController(app)

        self.assertFalse(controller.handle_close(app.window))
        self.assertEqual(app.holds, 0)

    def test_show_and_quit_release_background_hold(self):
        app = FakeApplication()
        controller = BackgroundController(app)
        controller._request_background_permission = lambda: None
        controller.handle_close(app.window)

        controller.show_window(app.window)
        self.assertTrue(app.window.presented)

        controller.quit()
        self.assertEqual(app.releases, 1)
        self.assertTrue(app.quit_called)
        self.assertTrue(controller.quitting)

    def test_disabling_preference_releases_hold(self):
        app = FakeApplication()
        controller = BackgroundController(app)
        controller._request_background_permission = lambda: None
        controller.handle_close(app.window)

        app.settings.enabled = False
        controller.sync_preference()

        self.assertEqual(app.releases, 1)


if __name__ == "__main__":
    unittest.main()
