# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Native context menu for adding library content to saved playlists."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gio, GLib, Gtk


class PlaylistContextMenu:
    """Attach a current, snapshot-safe playlist submenu to a widget."""

    def __init__(
        self,
        widget: Gtk.Widget,
        application,
        songs_provider,
        submenu_label=None,
        description_provider=None,
    ):
        self._widget = widget
        self._app = application
        self._manager = application.props.playlist_manager
        self._songs_provider = songs_provider
        self._submenu_label = submenu_label or _("Add to Playlist")
        self._description_provider = description_provider
        self._songs = []
        self._popover = None

        actions = Gio.SimpleActionGroup()
        add_action = Gio.SimpleAction.new(
            "add",
            GLib.VariantType.new("s"),
        )
        add_action.connect("activate", self._add_to_playlist)
        actions.add_action(add_action)
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self._create_playlist)
        actions.add_action(new_action)
        widget.insert_action_group("playlist-context", actions)
        self._actions = actions

        gesture = Gtk.GestureClick()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self._show)
        widget.add_controller(gesture)
        self._gesture = gesture
        self._unrealize_handler = widget.connect(
            "unrealize",
            self._on_widget_unrealize,
        )

    def _show(self, gesture, _press_count, x, y):
        self._songs = list(self._songs_provider() or [])
        if not self._songs:
            return
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self._close_popover()

        root = self._build_menu_model()

        popover = Gtk.PopoverMenu.new_from_model(root)
        popover.set_has_arrow(True)
        popover.set_parent(self._widget)
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x)
        rectangle.y = int(y)
        rectangle.width = 1
        rectangle.height = 1
        popover.set_pointing_to(rectangle)
        popover.connect("closed", self._on_popover_closed)
        self._popover = popover
        popover.popup()

    def _build_menu_model(self):
        root = Gio.Menu()
        playlists = Gio.Menu()
        model = self._manager.props.playlists
        for index in range(model.get_n_items()):
            playlist = model.get_item(index)
            item = Gio.MenuItem.new(playlist.props.name, None)
            item.set_action_and_target_value(
                "playlist-context.add",
                GLib.Variant("s", playlist.props.identifier),
            )
            playlists.append_item(item)

        if model.get_n_items() == 0:
            playlists.append(_("No playlists yet"), None)

        create = Gio.Menu()
        create.append(_("New Playlist…"), "playlist-context.new")
        playlists.append_section(None, create)
        root.append_submenu(self._label(), playlists)
        return root

    def _label(self):
        if callable(self._submenu_label):
            return self._submenu_label()
        return self._submenu_label

    def _description(self):
        if callable(self._description_provider):
            return self._description_provider()
        return self._description_provider or ""

    def _add_to_playlist(self, _action, parameter):
        playlist = self._find_playlist(parameter.get_string())
        if playlist is None:
            return
        added = self._manager.add_songs(playlist, self._songs)
        if added:
            message = _("Added %d song to %s") % (added, playlist.props.name)
            if added != 1:
                message = _("Added %d songs to %s") % (added, playlist.props.name)
        else:
            message = _("Already in %s") % playlist.props.name
        window = self._app.props.window
        if window is not None:
            window.show_message(message)

    def _create_playlist(self, *_args):
        self._app.add_to_playlist(
            self._songs,
            self._widget.get_root(),
            self._description(),
            focus_new=True,
        )

    def _find_playlist(self, identifier: str):
        model = self._manager.props.playlists
        for index in range(model.get_n_items()):
            playlist = model.get_item(index)
            if playlist.props.identifier == identifier:
                return playlist
        return None

    def _on_popover_closed(self, popover):
        if self._popover is popover:
            self._popover = None
        if popover.get_parent() is not None:
            popover.unparent()

    def _on_widget_unrealize(self, _widget):
        if self._popover is None:
            return
        popover = self._popover
        self._popover = None
        if popover.get_parent() is not None:
            popover.unparent()

    def _close_popover(self):
        if self._popover is None:
            return
        popover = self._popover
        self._popover = None
        popover.popdown()
