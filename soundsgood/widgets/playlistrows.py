# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Factory-backed rows used by the persistent playlist browser."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk, Pango

from soundsgood.widgets.songrow import format_duration, set_accessible_label


class PlaylistListItem(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        self._playlist = None
        self._handlers = []
        self.add_css_class("song-item")
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(9)
        self.set_margin_end(9)
        icon = Gtk.Image(icon_name="audio-x-generic-symbolic")
        icon.set_pixel_size(28)
        self.append(icon)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._name = Gtk.Label(xalign=0)
        self._name.set_ellipsize(Pango.EllipsizeMode.END)
        self._name.add_css_class("heading")
        labels.append(self._name)
        self._count = Gtk.Label(xalign=0)
        self._count.add_css_class("caption")
        self._count.add_css_class("dim-label")
        labels.append(self._count)
        self.append(labels)

    def bind(self, playlist):
        self.unbind()
        self._playlist = playlist
        self._handlers = [
            playlist.connect("notify::name", self._sync),
            playlist.connect("notify::entry-count", self._sync),
        ]
        self._sync()

    def unbind(self):
        if self._playlist is not None:
            for handler_id in self._handlers:
                if self._playlist.handler_is_connected(handler_id):
                    self._playlist.disconnect(handler_id)
        self._handlers.clear()
        self._playlist = None

    def _sync(self, *_args):
        if self._playlist is None:
            return
        self._name.set_label(self._playlist.props.name)
        self._count.set_label(_n_songs(self._playlist.props.entry_count))
        set_accessible_label(self, _("Open playlist %s") % self._playlist.props.name)


class PlaylistEntryItem(Gtk.Box):
    def __init__(self, on_play, on_move, on_remove):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._entry = None
        self._handlers = []
        self._on_play = on_play
        self._on_move = on_move
        self._on_remove = on_remove
        self.add_css_class("song-item")
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._play = Gtk.Button(icon_name="media-playback-start-symbolic")
        self._play.add_css_class("flat")
        self._play.add_css_class("row-play")
        self._play.set_valign(Gtk.Align.CENTER)
        self._play.connect(
            "clicked",
            lambda *_args: self._entry and self._on_play(self._entry),
        )
        self.append(self._play)

        self._cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        self._cover.set_pixel_size(34)
        self._cover.add_css_class("album-cover")
        self.append(self._cover)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._title = Gtk.Label(xalign=0)
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        self._title.add_css_class("song-title")
        labels.append(self._title)
        self._context = Gtk.Label(xalign=0)
        self._context.set_ellipsize(Pango.EllipsizeMode.END)
        self._context.add_css_class("caption")
        self._context.add_css_class("dim-label")
        labels.append(self._context)
        self.append(labels)

        self._duration = Gtk.Label(width_chars=6)
        self._duration.add_css_class("dim-label")
        self._duration.add_css_class("song-duration")
        self.append(self._duration)
        self._append_actions()

    def _append_actions(self):
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        actions_box.set_margin_top(6)
        actions_box.set_margin_bottom(6)
        actions_box.set_margin_start(6)
        actions_box.set_margin_end(6)
        for icon, direction, label in (
            ("go-up-symbolic", -1, _("Move up")),
            ("go-down-symbolic", 1, _("Move down")),
        ):
            button = Gtk.Button(label=label, icon_name=icon)
            button.add_css_class("flat")
            button.connect(
                "clicked",
                lambda _button, step=direction: self._move_from_menu(step),
            )
            actions_box.append(button)

        remove = Gtk.Button(
            label=_("Remove from playlist"),
            icon_name="edit-delete-symbolic",
        )
        remove.add_css_class("flat")
        remove.add_css_class("destructive-action")
        remove.connect("clicked", self._remove_from_menu)
        actions_box.append(remove)
        self._actions_popover = Gtk.Popover()
        self._actions_popover.set_child(actions_box)
        actions = Gtk.MenuButton(icon_name="view-more-symbolic")
        actions.add_css_class("flat")
        actions.add_css_class("compact-icon")
        actions.set_valign(Gtk.Align.CENTER)
        actions.set_tooltip_text(_("Playlist entry actions"))
        set_accessible_label(actions, _("Playlist entry actions"))
        actions.set_popover(self._actions_popover)
        self.append(actions)

    def bind(self, entry):
        self.unbind()
        self._entry = entry
        self._handlers = [
            entry.connect("notify::available", self._sync),
            entry.connect("notify::title", self._sync),
        ]
        self._sync()

    def unbind(self):
        if self._entry is not None:
            for handler_id in self._handlers:
                if self._entry.handler_is_connected(handler_id):
                    self._entry.disconnect(handler_id)
        self._handlers.clear()
        self._entry = None

    def _sync(self, *_args):
        if self._entry is None:
            return
        entry = self._entry
        basename = Gio.File.new_for_uri(entry.props.url).get_basename() or ""
        self._title.set_label(entry.props.title or basename)
        context = " — ".join(
            part for part in (entry.props.artist, entry.props.album) if part
        )
        if not entry.props.available:
            context = _("File unavailable") + (f" — {context}" if context else "")
            self.add_css_class("unavailable")
        else:
            self.remove_css_class("unavailable")
        self._context.set_label(context)
        self._duration.set_label(format_duration(entry.props.duration))
        self._play.set_sensitive(entry.props.available)
        if entry.props.thumbnail:
            self._cover.set_from_file(entry.props.thumbnail)
        else:
            self._cover.set_from_icon_name("audio-x-generic-symbolic")
        set_accessible_label(self, entry.props.title or _("Playlist song"))

    def _move_from_menu(self, step):
        self._actions_popover.popdown()
        if self._entry is not None:
            self._on_move(self._entry, step)

    def _remove_from_menu(self, _button):
        self._actions_popover.popdown()
        if self._entry is not None:
            self._on_remove(self._entry)


def create_playlist_factory():
    factory = Gtk.SignalListItemFactory()
    factory.connect("setup", lambda _factory, item: item.set_child(PlaylistListItem()))
    factory.connect("bind", lambda _factory, item: item.get_child().bind(item.get_item()))
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


def create_entry_factory(on_play, on_move, on_remove):
    factory = Gtk.SignalListItemFactory()
    factory.connect(
        "setup",
        lambda _factory, item: item.set_child(
            PlaylistEntryItem(on_play, on_move, on_remove)
        ),
    )
    factory.connect("bind", lambda _factory, item: item.get_child().bind(item.get_item()))
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


def _n_songs(count: int) -> str:
    return _("%d song") % count if count == 1 else _("%d songs") % count
