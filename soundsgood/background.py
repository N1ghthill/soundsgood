# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Application background lifecycle, independent from optional tray support."""

from __future__ import annotations

from gettext import gettext as _

from gi.repository import Gio, GLib

from soundsgood.diagnostics import get_logger


LOGGER = get_logger("background")


class BackgroundController:
    """Own application holds and make close-to-background deterministic."""

    def __init__(self, application):
        self._app = application
        self._settings = application.props.settings
        self._held = False
        self._quitting = False
        self._portal_requested = False
        self._portal_cancellable = Gio.Cancellable()

    @property
    def quitting(self):
        return self._quitting

    def handle_close(self, window):
        if self._quitting or not self._settings.get_boolean("run-in-background"):
            return False

        if not self._held:
            self._app.hold()
            self._held = True
        window.set_visible(False)
        self._request_background_permission()
        self._notify_background()
        LOGGER.info("Main window hidden; application remains in background")
        return True

    def show_window(self, window):
        self._app.withdraw_notification("running-in-background")
        window.present()

    def quit(self):
        self._quitting = True
        self._app.withdraw_notification("running-in-background")
        if self._held:
            self._app.release()
            self._held = False
        self._app.quit()

    def sync_preference(self):
        if self._settings.get_boolean("run-in-background") or not self._held:
            return
        self._app.release()
        self._held = False

    def shutdown(self):
        self._quitting = True
        self._portal_cancellable.cancel()
        self._held = False

    def _notify_background(self):
        notification = Gio.Notification.new(_("SoundsGood is still running"))
        notification.set_body(
            _("Playback and media controls remain available in the background.")
        )
        notification.add_button(_("Open SoundsGood"), "app.show")
        self._app.send_notification("running-in-background", notification)

    def _request_background_permission(self):
        if self._portal_requested:
            return
        self._portal_requested = True
        try:
            proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
                None,
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Background",
                None,
            )
            options = {
                "reason": GLib.Variant(
                    "s", _("Continue local music playback after closing the window")
                ),
                "autostart": GLib.Variant("b", False),
            }
            proxy.call(
                "RequestBackground",
                GLib.Variant("(sa{sv})", ("", options)),
                Gio.DBusCallFlags.NONE,
                -1,
                self._portal_cancellable,
                self._on_background_requested,
            )
        except GLib.Error:
            LOGGER.info("Background portal is unavailable", exc_info=True)

    def _on_background_requested(self, proxy, result):
        if self._quitting:
            return
        try:
            proxy.call_finish(result)
        except GLib.Error:
            LOGGER.info("Desktop did not accept the background request")
