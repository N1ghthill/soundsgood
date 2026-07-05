# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk

from soundsgood.views.albumsview import AlbumsView
from soundsgood.views.artistsview import ArtistsView
from soundsgood.views.songsview import SongsView
from soundsgood.widgets.playertoolbar import PlayerToolbar
from soundsgood.widgets.searchview import SearchView


class Window(Adw.ApplicationWindow):
    """Main SoundsGood window."""

    def __init__(self, application):
        super().__init__(application=application)
        self._app = application
        self._settings = application.props.settings
        self.set_title(_("SoundsGood"))
        self.set_default_size(
            self._settings.get_int("window-width"),
            self._settings.get_int("window-height"),
        )
        if self._settings.get_boolean("window-maximized"):
            self.maximize()

        self._toolbar_view = Adw.ToolbarView()
        self.set_content(self._toolbar_view)

        self._headerbar = Adw.HeaderBar()
        self._toolbar_view.add_top_bar(self._headerbar)

        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self._switcher = Gtk.StackSwitcher()
        self._switcher.set_stack(self._stack)
        self._headerbar.set_title_widget(self._switcher)

        self._search_button = Gtk.Button(icon_name="system-search-symbolic")
        self._search_button.set_tooltip_text(_("Search"))
        self._search_button.connect("clicked", self._show_search)
        self._headerbar.pack_end(self._search_button)

        menu = Gio.Menu()
        menu.append(_("Preferences"), "app.preferences")
        menu.append(_("About SoundsGood"), "app.about")
        self._menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self._menu_button.set_menu_model(menu)
        self._headerbar.pack_end(self._menu_button)

        self._albums_view = AlbumsView(application)
        self._artists_view = ArtistsView(application)
        self._songs_view = SongsView(application)
        self._search_view = SearchView(application)

        self._stack.add_titled(self._albums_view, "albums", _("Albums"))
        self._stack.add_titled(self._artists_view, "artists", _("Artists"))
        self._stack.add_titled(self._songs_view, "songs", _("Songs"))
        self._stack.add_titled(self._search_view, "search", _("Search"))

        self._player_toolbar = PlayerToolbar(application)
        application.props.player.connect("error", self._on_player_error)
        application.props.library.connect("scan-error", self._on_library_error)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._stack)
        content.append(self._player_toolbar)
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(content)
        self._toolbar_view.set_content(self._toast_overlay)

        self.connect("close-request", self._on_close_request)

    def _show_search(self, _button):
        self._stack.set_visible_child_name("search")
        self._search_view.grab_search_focus()

    def _on_close_request(self, *_args):
        width, height = self.get_default_size()
        self._settings.set_int("window-width", width)
        self._settings.set_int("window-height", height)
        self._settings.set_boolean("window-maximized", self.is_maximized())
        return False

    def _on_player_error(self, _player, message):
        toast = Adw.Toast.new(message)
        self._toast_overlay.add_toast(toast)

    def _on_library_error(self, _library, message):
        toast = Adw.Toast.new(message)
        self._toast_overlay.add_toast(toast)
