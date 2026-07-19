# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from soundsgood.models import LibraryState, Song
from soundsgood.widgets.songrow import create_song_factory, set_accessible_label


class SongsView(Adw.Bin):
    """List of all songs."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player

        self._stack = Gtk.Stack()
        self._selection = Gtk.NoSelection.new(self._library.props.songs)
        self._listview = Gtk.ListView.new(
            self._selection,
            create_song_factory(
                self._player,
                self._play_song,
                show_context=True,
                on_add=self._add_song,
                application=self._app,
            ),
        )
        self._listview.set_single_click_activate(False)
        self._listview.connect("activate", self._on_item_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._listview)
        self._stack.add_named(scrolled, "songs")

        self._status = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._status.set_halign(Gtk.Align.CENTER)
        self._status.set_valign(Gtk.Align.CENTER)
        self._status_label = Gtk.Label()
        self._status_label.add_css_class("dim-label")
        self._status.append(self._status_label)
        self._choose_button = Gtk.Button(label=_("Choose Music Folder"))
        self._choose_button.set_icon_name("folder-music-symbolic")
        self._choose_button.add_css_class("suggested-action")
        self._choose_button.add_css_class("compact-pill")
        self._choose_button.connect("clicked", self._on_choose_folder_clicked)
        set_accessible_label(self._choose_button, _("Choose Music Folder"))
        self._status.append(self._choose_button)
        self._stack.add_named(self._status, "status")
        self.set_child(self._stack)

        self._library.connect("scan-started", self._on_scan_started)
        self._library.connect("scan-finished", self._on_scan_finished)
        self._library.connect("scan-error", self._on_scan_error)
        self._rebuild()

    def _on_scan_started(self, *_args):
        self._show_status()

    def _on_scan_finished(self, *_args):
        self._rebuild()

    def _on_scan_error(self, *_args):
        self._show_status()

    def _show_status(self):
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No songs found")
        self._status_label.set_label(message)
        self._choose_button.set_visible(
            self._library.props.scan_state != int(LibraryState.SCANNING)
        )
        self._stack.set_visible_child_name("status")

    def _rebuild(self):
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        if self._library.props.songs.get_n_items() == 0:
            self._status_label.set_label(self._library.props.status_message or _("No songs found"))
            self._choose_button.set_visible(True)
            self._stack.set_visible_child_name("status")
            return
        self._stack.set_visible_child_name("songs")

    def _on_item_activated(self, _listview, position):
        song = self._library.props.songs.get_item(position)
        if isinstance(song, Song):
            self._play_song(song)

    def _play_song(self, song):
        self._player.play_song(song, self._library.get_all_songs())

    def _add_song(self, song):
        self._app.add_to_playlist(
            [song],
            self.get_root(),
            _("Add %s to a saved playlist") % song.props.title,
        )

    def _on_choose_folder_clicked(self, _button):
        self._app.select_music_folder(self.get_root())
