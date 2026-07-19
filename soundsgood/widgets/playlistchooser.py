# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Small adaptive dialog for adding library content to a saved playlist."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from soundsgood.widgets.songrow import set_accessible_label


class PlaylistChooserDialog(Adw.Dialog):
    def __init__(
        self,
        application,
        songs,
        description: str = "",
        focus_new=False,
    ):
        super().__init__(title=_("Add to Playlist"))
        self.set_content_width(390)
        self.set_content_height(480)
        self._app = application
        self._manager = application.props.playlist_manager
        self._songs = list(songs)
        self._description = description
        self._manager_handlers = [
            self._manager.connect("loaded", self._rebuild),
            self._manager.connect("changed", self._rebuild),
        ]

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        if description:
            label = Gtk.Label(label=description, xalign=0)
            label.set_wrap(True)
            label.add_css_class("dim-label")
            content.append(label)

        create_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_hexpand(True)
        self._name_entry.set_placeholder_text(_("New playlist name"))
        self._name_entry.connect("activate", self._create_playlist)
        create_box.append(self._name_entry)
        create_button = Gtk.Button(icon_name="list-add-symbolic")
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("compact-icon")
        create_button.set_tooltip_text(_("Create playlist"))
        set_accessible_label(create_button, _("Create playlist"))
        create_button.connect("clicked", self._create_playlist)
        create_box.append(create_button)
        content.append(create_box)

        self._list = Gtk.ListBox()
        self._list.add_css_class("boxed-list")
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.connect("row-activated", self._playlist_activated)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self._list)
        content.append(scroller)

        self._status = Gtk.Label()
        self._status.set_wrap(True)
        self._status.add_css_class("dim-label")
        content.append(self._status)

        toolbar.set_content(content)
        self.set_child(toolbar)
        self._rebuild()
        if focus_new:
            self._name_entry.grab_focus()

    def do_unroot(self):
        for handler_id in self._manager_handlers:
            if self._manager.handler_is_connected(handler_id):
                self._manager.disconnect(handler_id)
        self._manager_handlers.clear()
        Adw.Dialog.do_unroot(self)

    def _rebuild(self, *_args):
        row = self._list.get_first_child()
        while row:
            self._list.remove(row)
            row = self._list.get_first_child()
        model = self._manager.props.playlists
        for index in range(model.get_n_items()):
            playlist = model.get_item(index)
            row = Adw.ActionRow(
                title=playlist.props.name,
                subtitle=_n_songs(playlist.props.entry_count),
                activatable=True,
            )
            row.playlist = playlist
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            self._list.append(row)
        if not self._manager.props.loaded:
            self._status.set_label(_("Loading playlists..."))
        elif model.get_n_items() == 0:
            self._status.set_label(_("Create your first playlist above."))
        else:
            self._status.set_label("")

    def _playlist_activated(self, _list, row):
        playlist = getattr(row, "playlist", None)
        if playlist is None:
            return
        added = self._manager.add_songs(playlist, self._songs)
        if added:
            self._notify(_("Added %d songs to %s") % (added, playlist.props.name))
            self.close()
        else:
            self._status.set_label(_("No local songs could be added."))

    def _create_playlist(self, _widget):
        name = self._name_entry.get_text().strip()
        if not name:
            self._status.set_label(_("Enter a playlist name."))
            return
        try:
            playlist = self._manager.create(name, self._songs)
        except ValueError as error:
            self._status.set_label(str(error))
            return
        self._notify(_("Created playlist %s") % playlist.props.name)
        self.close()

    def _notify(self, message: str):
        window = self._app.props.window
        if window is not None:
            window.show_message(message)


def _n_songs(count: int) -> str:
    return _("%d song") % count if count == 1 else _("%d songs") % count
