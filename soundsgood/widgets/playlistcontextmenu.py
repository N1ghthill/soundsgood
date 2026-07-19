# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Native context menu for adding library content to saved playlists."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk, Pango


class PlaylistContextMenu:
    """Attach a current, snapshot-safe playlist destination popover."""

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

        popover = Gtk.Popover()
        popover.set_has_arrow(True)
        popover.add_css_class("playlist-context-popover")
        popover.set_parent(self._widget)
        popover.set_child(self._build_content())
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x)
        rectangle.y = int(y)
        rectangle.width = 1
        rectangle.height = 1
        popover.set_pointing_to(rectangle)
        popover.connect("closed", self._on_popover_closed)
        self._popover = popover
        popover.popup()

    def _build_content(self):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content.set_margin_top(5)
        content.set_margin_bottom(5)
        content.set_margin_start(5)
        content.set_margin_end(5)

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        header.add_css_class("playlist-context-header")
        heading = Gtk.Label(label=self._label(), xalign=0)
        heading.add_css_class("heading")
        header.append(heading)

        model = self._manager.props.playlists
        destination_count = model.get_n_items()
        hint = Gtk.Label(
            label=_playlist_count(destination_count),
            xalign=0,
        )
        hint.add_css_class("caption")
        hint.add_css_class("dim-label")
        header.append(hint)
        content.append(header)

        if destination_count:
            selection = Gtk.NoSelection.new(model)
            destinations = Gtk.ListView.new(
                selection,
                _create_destination_factory(self._activate_playlist),
            )
            destinations.add_css_class("playlist-destination-list")
            destinations.set_single_click_activate(False)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_width(272)
            scroller.set_max_content_height(276)
            scroller.set_propagate_natural_height(True)
            scroller.set_child(destinations)
            content.append(scroller)
        else:
            empty = Gtk.Label(label=_("No playlists yet"), xalign=0)
            empty.add_css_class("dim-label")
            empty.set_margin_top(10)
            empty.set_margin_bottom(10)
            empty.set_margin_start(8)
            empty.set_margin_end(8)
            content.append(empty)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(2)
        separator.set_margin_bottom(2)
        content.append(separator)
        create = Gtk.Button(
            label=_("New Playlist…"),
            icon_name="list-add-symbolic",
        )
        create.add_css_class("flat")
        create.add_css_class("playlist-create")
        create.set_halign(Gtk.Align.FILL)
        create.connect("clicked", self._create_playlist)
        content.append(create)
        return content

    def _label(self):
        if callable(self._submenu_label):
            return self._submenu_label()
        return self._submenu_label

    def _description(self):
        if callable(self._description_provider):
            return self._description_provider()
        return self._description_provider or ""

    def _activate_playlist(self, playlist):
        self._close_popover()
        try:
            added = self._manager.add_songs(playlist, self._songs)
        except ValueError as error:
            message = str(error)
        else:
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
        parent = self._widget.get_root()
        self._close_popover()
        self._app.add_to_playlist(
            self._songs,
            parent,
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


class _PlaylistDestination(Gtk.Button):
    def __init__(self, on_activate):
        super().__init__()
        self._playlist = None
        self._name_handler = 0
        self._count_handler = 0
        self._on_activate = on_activate
        self.add_css_class("flat")
        self.add_css_class("playlist-destination")
        self.set_halign(Gtk.Align.FILL)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        icon = Gtk.Image.new_from_icon_name("view-list-symbolic")
        icon.set_pixel_size(18)
        icon.add_css_class("playlist-destination-icon")
        row.append(icon)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        labels.set_hexpand(True)
        labels.set_valign(Gtk.Align.CENTER)
        self._name = Gtk.Label(xalign=0)
        self._name.set_ellipsize(Pango.EllipsizeMode.END)
        self._name.set_single_line_mode(True)
        self._name.add_css_class("playlist-destination-name")
        labels.append(self._name)
        self._count = Gtk.Label(xalign=0)
        self._count.add_css_class("caption")
        self._count.add_css_class("dim-label")
        labels.append(self._count)
        row.append(labels)

        add_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        add_icon.set_pixel_size(16)
        add_icon.add_css_class("dim-label")
        row.append(add_icon)
        self.set_child(row)
        self.connect("clicked", self._clicked)

    def bind(self, playlist):
        self.unbind()
        self._playlist = playlist
        self._name_handler = playlist.connect("notify::name", self._sync)
        self._count_handler = playlist.connect(
            "notify::entry-count",
            self._sync,
        )
        self._sync()

    def unbind(self):
        if self._playlist is not None and self._name_handler:
            if self._playlist.handler_is_connected(self._name_handler):
                self._playlist.disconnect(self._name_handler)
        if self._playlist is not None and self._count_handler:
            if self._playlist.handler_is_connected(self._count_handler):
                self._playlist.disconnect(self._count_handler)
        self._name_handler = 0
        self._count_handler = 0
        self._playlist = None

    def _sync(self, *_args):
        if self._playlist is not None:
            self._name.set_label(self._playlist.props.name)
            self._count.set_label(_song_count(self._playlist.props.entry_count))
            self.set_tooltip_text(_("Add to %s") % self._playlist.props.name)

    def _clicked(self, _button):
        if self._playlist is not None:
            self._on_activate(self._playlist)


def _create_destination_factory(on_activate):
    factory = Gtk.SignalListItemFactory()
    factory.connect(
        "setup",
        lambda _factory, item: item.set_child(_PlaylistDestination(on_activate)),
    )
    factory.connect(
        "bind",
        lambda _factory, item: item.get_child().bind(item.get_item()),
    )
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


def _playlist_count(count):
    if count == 1:
        return _("1 playlist available")
    return _("%d playlists available") % count


def _song_count(count):
    if count == 1:
        return _("1 song")
    return _("%d songs") % count
