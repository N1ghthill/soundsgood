# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from soundsgood.models import LibraryState, Song
from soundsgood.widgets.songrow import SongRow


class SongsView(Adw.Bin):
    """List of all songs."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.set_activate_on_single_click(False)
        self._listbox.connect("row-activated", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._listbox)
        self.set_child(scrolled)

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
        self._clear()
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No songs found")
        self._listbox.append(self._placeholder(message))

    def _rebuild(self):
        self._clear()
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        songs = self._library.get_all_songs()
        if not songs:
            self._listbox.append(self._placeholder(self._library.props.status_message or _("No songs found")))
            return

        for song in songs:
            self._listbox.append(
                SongRow(
                    song,
                    show_context=True,
                    on_activate=self._play_song,
                    player=self._player,
                )
            )

    def _placeholder(self, text):
        placeholder = Gtk.Label(label=text)
        placeholder.set_margin_top(48)
        placeholder.add_css_class("dim-label")
        return placeholder

    def _clear(self):
        child = self._listbox.get_first_child()
        while child:
            self._listbox.remove(child)
            child = self._listbox.get_first_child()

    def _on_row_activated(self, _listbox, row):
        song = getattr(row, "song", None)
        if isinstance(song, Song):
            self._play_song(song)

    def _play_song(self, song):
        self._player.play_song(song, self._library.get_all_songs())
