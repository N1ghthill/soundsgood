# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import gi
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")

from gettext import gettext as _
from gi.repository import Adw, GLib, GObject, Gdk, Gio, Gtk, Gst

from soundsgood.player import Player
from soundsgood.library import Library
from soundsgood.mpris import MprisService
from soundsgood.models import PlayState, RepeatMode
from soundsgood.background import BackgroundController
from soundsgood.playlists import PlaylistManager
from soundsgood.widgets.preferencesdialog import PreferencesDialog
from soundsgood.widgets.aboutdialog import AboutDialog
from soundsgood.diagnostics import configure_logging, diagnostics_file, get_logger


LOGGER = get_logger("application")


class MemorySettings:
    """Small development fallback when GSettings schemas are not installed."""

    _defaults = {
        "repeat": 0,
        "volume": 1.0,
        "mute": False,
        "window-width": 1200,
        "window-height": 800,
        "window-maximized": False,
        "music-dir": "",
        "color-scheme": "system",
        "enable-notifications": True,
        "inhibit-suspend": True,
        "run-in-background": True,
    }

    def __init__(self):
        self._values = dict(self._defaults)

    def get_string(self, key):
        return str(self._values.get(key, ""))

    def set_string(self, key, value):
        self._values[key] = value

    def get_double(self, key):
        return float(self._values.get(key, 0.0))

    def set_double(self, key, value):
        self._values[key] = float(value)

    def get_boolean(self, key):
        return bool(self._values.get(key, False))

    def set_boolean(self, key, value):
        self._values[key] = bool(value)

    def get_int(self, key):
        return int(self._values.get(key, 0))

    def set_int(self, key, value):
        self._values[key] = int(value)

    def get_enum(self, key):
        return int(self._values.get(key, 0))

    def set_enum(self, key, value):
        self._values[key] = int(value)


class SoundsGoodApplication(Adw.Application):
    """Main application class for SoundsGood."""

    def __init__(self, application_id, version):
        super().__init__(
            application_id=application_id,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.props.resource_base_path = "/io/github/n1ghthill/soundsgood"
        GLib.set_application_name(_("SoundsGood"))
        GLib.set_prgname(application_id)
        GLib.setenv("PULSE_PROP_application.id", application_id, True)

        self._version = version
        self._window = None
        self._settings = self._create_settings()
        self._settings_changed_handler = None
        self._inhibit_cookie = 0
        self._last_notification_url = ""

        # Initialize GStreamer
        Gst.init(None)

        # Core components
        self._library = Library(self)
        self._player = Player(self)
        self._playlist_manager = PlaylistManager()
        self._mpris = MprisService(self)
        self._background = BackgroundController(self)
        self._status_notifier = None
        self._player_handlers = [
            self._player.connect(
                "notify::current-song", self._on_player_activity_changed
            ),
            self._player.connect("notify::play-state", self._on_player_activity_changed),
        ]
        self._library_handlers = [
            self._library.connect(
                "scan-finished",
                lambda *_args: self._playlist_manager.refresh_availability(
                    self._library
                ),
            ),
            self._library.connect(
                "scan-error",
                lambda *_args: self._playlist_manager.refresh_availability(
                    self._library
                ),
            ),
        ]
        self._playlist_handlers = [
            self._playlist_manager.connect(
                "loaded",
                lambda *_args: self._playlist_manager.refresh_availability(
                    self._library
                ),
            )
        ]

        self._setup_actions()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def library(self):
        return self._library

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def player(self):
        return self._player

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def playlist_manager(self):
        return self._playlist_manager

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def window(self):
        return self._window

    def _setup_actions(self):
        action_entries = [
            ("about", self._on_about, ("app.about", ["F1"])),
            ("preferences", self._on_preferences, ("app.preferences", ["<Ctrl>comma"])),
            ("quit", self._on_quit, ("app.quit", ["<Ctrl>Q"])),
            ("show", self._on_show, None),
            ("select_music_folder", self._on_select_music_folder, None),
            ("reindex_library", self._on_reindex_library, ("app.reindex_library", ["<Ctrl><Shift>R"])),
            ("play_pause", self._on_play_pause, ("app.play_pause", ["<Ctrl>space", "AudioPlay", "AudioPause"])),
            ("song_next", self._on_song_next, ("app.song_next", ["<Ctrl>N", "AudioNext"])),
            ("song_previous", self._on_song_previous, ("app.song_previous", ["<Ctrl>B", "AudioPrev"])),
            ("volume_up", self._on_volume_up, ("app.volume_up", ["<Ctrl>plus", "<Ctrl>equal"])),
            ("volume_down", self._on_volume_down, ("app.volume_down", ["<Ctrl>minus"])),
            ("mute", self._on_mute, ("app.mute", ["<Ctrl>M"])),
            ("repeat_toggle", self._on_repeat_toggle, ("app.repeat_toggle", ["<Ctrl>R"])),
            ("shuffle_toggle", self._on_shuffle_toggle, ("app.shuffle_toggle", ["<Ctrl>S"])),
        ]

        for action_name, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action_name, None)
            simple_action.connect("activate", callback)
            self.add_action(simple_action)
            if accel:
                self.set_accels_for_action(*accel)

    def _on_about(self, action, param):
        dialog = AboutDialog(self._version)
        dialog.present(self._window)

    def _on_preferences(self, action, param):
        dialog = PreferencesDialog(self)
        dialog.present(self._window)

    def _on_quit(self, action, param):
        self.quit_application()

    def _on_show(self, action, param):
        self.show_main_window()

    def _on_select_music_folder(self, action, param):
        self.select_music_folder(self._window)

    def _on_reindex_library(self, action, param):
        self.reindex_library()

    def _on_play_pause(self, action, param):
        self._player.play_pause()

    def _on_song_next(self, action, param):
        self._player.next()

    def _on_song_previous(self, action, param):
        self._player.previous()

    def _on_volume_up(self, action, param):
        vol = min(1.0, self._player.props.volume + 0.05)
        self._player.props.volume = vol

    def _on_volume_down(self, action, param):
        vol = max(0.0, self._player.props.volume - 0.05)
        self._player.props.volume = vol

    def _on_mute(self, action, param):
        self._player.props.mute = not self._player.props.mute

    def _on_repeat_toggle(self, action, param):
        modes = [RepeatMode.NONE, RepeatMode.ALL, RepeatMode.SONG]
        current = self._player.props.repeat_mode
        idx = (modes.index(current) + 1) % len(modes) if current in modes else 0
        self._player.props.repeat_mode = int(modes[idx])

    def _on_shuffle_toggle(self, action, param):
        current = self._player.props.repeat_mode
        if current == RepeatMode.SHUFFLE:
            self._player.props.repeat_mode = int(RepeatMode.NONE)
        else:
            self._player.props.repeat_mode = int(RepeatMode.SHUFFLE)

    def _create_settings(self):
        schema_id = os.environ.get("RDNN_NAME", "io.github.n1ghthill.soundsgood")
        schema_source = Gio.SettingsSchemaSource.get_default()
        if schema_source and schema_source.lookup(schema_id, True):
            return Gio.Settings.new(schema_id)

        return MemorySettings()

    def select_music_folder(self, parent=None, on_selected=None):
        dialog = Gtk.FileDialog(title=_("Select Music Folder"))
        dialog.select_folder(
            parent or self._window,
            None,
            lambda file_dialog, result: self._on_music_folder_selected(
                file_dialog,
                result,
                on_selected,
            ),
        )

    def _on_music_folder_selected(self, dialog, result, on_selected=None):
        try:
            folder = dialog.select_folder_finish(result)
        except Exception:
            return

        path = folder.get_path()
        if not path:
            return

        self._settings.set_string("music-dir", path)
        self._library.scan(path, force=True, refresh_metadata=True)
        if on_selected:
            on_selected(path)

    def reindex_library(self):
        self._library.scan(force=True, refresh_metadata=True)

    def add_to_playlist(
        self,
        songs,
        parent=None,
        description="",
        focus_new=False,
    ):
        from soundsgood.widgets.playlistchooser import PlaylistChooserDialog

        dialog = PlaylistChooserDialog(self, songs, description, focus_new=focus_new)
        dialog.present(parent or self._window)

    def apply_color_scheme(self):
        scheme = self._settings.get_string("color-scheme")
        style_manager = Adw.StyleManager.get_default()
        if scheme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        elif scheme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def sync_desktop_integration(self):
        self._sync_suspend_inhibition()
        self._background.sync_preference()

    def handle_close_request(self, window):
        return self._background.handle_close(window)

    def show_main_window(self):
        self._ensure_window()
        self._background.show_window(self._window)

    def quit_application(self):
        self._background.quit()

    def _on_player_activity_changed(self, *_args):
        self._sync_suspend_inhibition()
        self._send_now_playing_notification()

    def _sync_suspend_inhibition(self):
        should_inhibit = (
            self._settings.get_boolean("inhibit-suspend")
            and self._player.props.play_state == int(PlayState.PLAYING)
            and self._player.props.current_song is not None
            and self._window is not None
        )

        if should_inhibit and not self._inhibit_cookie:
            self._inhibit_cookie = self.inhibit(
                self._window,
                Gtk.ApplicationInhibitFlags.SUSPEND,
                _("Music is playing"),
            )
        elif not should_inhibit and self._inhibit_cookie:
            self.uninhibit(self._inhibit_cookie)
            self._inhibit_cookie = 0

    def _send_now_playing_notification(self):
        song = self._player.props.current_song
        if self._player.props.play_state != int(PlayState.PLAYING):
            self.withdraw_notification("now-playing")
            return
        if song is None or not self._settings.get_boolean("enable-notifications"):
            return
        if song.props.url and song.props.url == self._last_notification_url:
            return

        notification = Gio.Notification.new(song.props.title or _("Now Playing"))
        body_parts = [part for part in (song.props.artist, song.props.album) if part]
        if body_parts:
            notification.set_body(" - ".join(body_parts))
        if song.props.thumbnail:
            notification.set_icon(Gio.FileIcon.new(Gio.File.new_for_path(song.props.thumbnail)))

        self._last_notification_url = song.props.url
        self.send_notification("now-playing", notification)

    def do_startup(self):
        LOGGER.info("Application startup")
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(self.get_application_id())
        self.apply_color_scheme()
        if hasattr(self._settings, "connect"):
            self._settings_changed_handler = self._settings.connect(
                "changed::color-scheme",
                lambda *_args: self.apply_color_scheme(),
            )

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        from soundsgood.statusnotifier import StatusNotifierService

        self._status_notifier = StatusNotifierService(self)

    def do_activate(self):
        LOGGER.info("Application activate")
        self._ensure_window()

        # Start library scan
        self._library.scan()
        self._sync_suspend_inhibition()
        self.show_main_window()

    def do_open(self, files, n_files, hint):
        LOGGER.info("Opening %d external file(s)", n_files)
        self._ensure_window()

        # Keep the library available while treating opened files as a temporary queue.
        self._library.scan()
        self._open_files(files)
        self.show_main_window()

    def _ensure_window(self):
        if not self._window:
            from soundsgood.window import Window
            self._window = Window(self)

    def _open_files(self, files):
        songs = []
        for file in files:
            songs.extend(self._library.create_songs_for_file(file))

        if not songs:
            if self._window:
                self._window.show_message(_("No playable audio files"))
            return

        self._player.play_song(songs[0], songs)

    def do_shutdown(self):
        LOGGER.info("Application shutdown")
        self._background.shutdown()
        if self._status_notifier:
            self._status_notifier.shutdown()
            self._status_notifier = None
        for handler_id in self._player_handlers:
            if self._player.handler_is_connected(handler_id):
                self._player.disconnect(handler_id)
        self._player_handlers.clear()
        for handler_id in self._library_handlers:
            if self._library.handler_is_connected(handler_id):
                self._library.disconnect(handler_id)
        self._library_handlers.clear()
        for handler_id in self._playlist_handlers:
            if self._playlist_manager.handler_is_connected(handler_id):
                self._playlist_manager.disconnect(handler_id)
        self._playlist_handlers.clear()
        if self._settings_changed_handler and hasattr(self._settings, "disconnect"):
            self._settings.disconnect(self._settings_changed_handler)
            self._settings_changed_handler = None
        if self._inhibit_cookie:
            self.uninhibit(self._inhibit_cookie)
            self._inhibit_cookie = 0
        self.withdraw_notification("now-playing")
        self._mpris.shutdown()
        self._playlist_manager.shutdown()
        self._library.shutdown()
        self._player.shutdown()
        Adw.Application.do_shutdown(self)


def main():
    application_id = os.environ.get("APPLICATION_ID", "io.github.n1ghthill.soundsgood")
    version = os.environ.get("VERSION", "0.2.2")

    logger = configure_logging(version)
    try:
        app = SoundsGoodApplication(application_id, version)
        return app.run(sys.argv)
    except Exception:
        logger.critical(
            "SoundsGood could not start; diagnostics=%s",
            diagnostics_file(),
            exc_info=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
