# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")
gi.require_version("GstAudio", "1.0")

from gettext import gettext as _
from gi.repository import Adw, GLib, GObject, Gdk, Gio, Gtk, Gst

from soundsgood.player import Player
from soundsgood.library import Library
from soundsgood.mpris import MprisService
from soundsgood.models import RepeatMode
from soundsgood.views.albumsview import AlbumsView
from soundsgood.views.artistsview import ArtistsView
from soundsgood.views.songsview import SongsView
from soundsgood.widgets.playertoolbar import PlayerToolbar
from soundsgood.widgets.searchview import SearchView
from soundsgood.widgets.preferencesdialog import PreferencesDialog
from soundsgood.widgets.aboutdialog import AboutDialog


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
        "color-scheme": "light",
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
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.props.resource_base_path = "/io/github/n1ghthill/soundsgood"
        GLib.set_application_name(_("SoundsGood"))
        GLib.set_prgname(application_id)
        GLib.setenv("PULSE_PROP_application.id", application_id, True)

        self._version = version
        self._window = None
        self._settings = self._create_settings()
        self._settings_changed_handler = None

        # Initialize GStreamer
        Gst.init(None)

        # Core components
        self._library = Library(self)
        self._player = Player(self)
        self._mpris = MprisService(self)

        # Views
        self._albums_view = None
        self._artists_view = None
        self._songs_view = None
        self._search_view = None

        self._setup_actions()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def library(self):
        return self._library

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def player(self):
        return self._player

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
        if self._window:
            self._window.destroy()

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

    def apply_color_scheme(self):
        scheme = self._settings.get_string("color-scheme")
        style_manager = Adw.StyleManager.get_default()
        if scheme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.apply_color_scheme()
        if hasattr(self._settings, "connect"):
            self._settings_changed_handler = self._settings.connect(
                "changed::color-scheme",
                lambda *_args: self.apply_color_scheme(),
            )

        # Load CSS
        css_provider = Gtk.CssProvider()
        css = b"""
        .album-cover {
            border-radius: 8px;
        }
        .artist-avatar {
            border-radius: 50%;
        }
        .player-toolbar {
            background: alpha(@window_bg_color, 0.95);
            border-top: 1px solid @borders;
        }
        row.playing {
            background: alpha(@accent_color, 0.12);
        }
        row.playing label.song-title {
            color: @accent_color;
            font-weight: 700;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        if not self._window:
            from soundsgood.window import Window
            self._window = Window(self)

        # Start library scan
        self._library.scan()
        self._window.present()

    def do_shutdown(self):
        self._mpris.shutdown()
        Adw.Application.do_shutdown(self)


def main():
    application_id = os.environ.get("APPLICATION_ID", "io.github.n1ghthill.soundsgood")
    version = os.environ.get("VERSION", "0.1.0")

    app = SoundsGoodApplication(application_id, version)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
