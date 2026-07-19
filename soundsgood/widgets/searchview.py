# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk, Pango

from soundsgood.widgets.songrow import SongRow


class SearchView(Adw.Bin):
    """Global library search."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._search_source_id = 0

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)

        self._entry = Gtk.SearchEntry()
        self._entry.set_placeholder_text(_("Search songs, albums, artists..."))
        self._entry.connect("search-changed", self._on_search_changed)
        box.append(self._entry)

        self._results = Gtk.ListBox()
        self._results.add_css_class("boxed-list")
        self._results.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._results.set_activate_on_single_click(False)
        self._results.connect("row-activated", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self._results)
        scrolled.set_vexpand(True)
        box.append(scrolled)

        self.set_child(box)

    def grab_search_focus(self):
        self._entry.grab_focus()

    def _on_search_changed(self, entry):
        if self._search_source_id:
            GLib.source_remove(self._search_source_id)
        query = entry.get_text().strip()
        self._search_source_id = GLib.timeout_add(180, self._run_search, query)

    def _run_search(self, query):
        self._search_source_id = 0
        self._clear()
        if not query:
            return GLib.SOURCE_REMOVE

        results = self._library.search(query)
        albums = self._library.search_albums(query)
        artists = self._library.search_artists(query)

        if artists:
            self._append_section(_("Artists"))
            for artist in artists[:20]:
                self._results.append(self._artist_row(artist))

        if albums:
            self._append_section(_("Albums"))
            for album in albums[:30]:
                self._results.append(self._album_row(album))

        if results.get_n_items() > 0:
            self._append_section(_("Songs"))
        for index in range(min(results.get_n_items(), 100)):
            self._results.append(
                SongRow(
                    results.get_item(index),
                    show_context=True,
                    on_activate=self._play_song,
                    player=self._player,
                )
            )
        return GLib.SOURCE_REMOVE

    def do_unroot(self):
        if self._search_source_id:
            GLib.source_remove(self._search_source_id)
            self._search_source_id = 0
        Adw.Bin.do_unroot(self)

    def _clear(self):
        child = self._results.get_first_child()
        while child:
            self._results.remove(child)
            child = self._results.get_first_child()

    def _append_section(self, title: str):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)

        label = Gtk.Label(label=title, xalign=0)
        label.add_css_class("heading")
        label.set_margin_top(9)
        label.set_margin_bottom(4)
        label.set_margin_start(9)
        label.set_margin_end(9)
        row.set_child(label)
        self._results.append(row)

    def _artist_row(self, artist):
        row = Gtk.ListBoxRow()
        row.artist = artist
        row.result_type = "artist"

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(9)
        box.set_margin_end(9)

        image = Gtk.Image(icon_name="avatar-default-symbolic")
        image.set_pixel_size(34)
        image.add_css_class("artist-avatar")
        box.append(image)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        name = Gtk.Label(label=artist.props.name, xalign=0)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(name)
        summary = Gtk.Label(
            label=_("%d albums, %d songs") % (
                artist.props.album_count,
                artist.props.song_count,
            ),
            xalign=0,
        )
        summary.add_css_class("caption")
        summary.add_css_class("dim-label")
        labels.append(summary)
        box.append(labels)

        row.set_child(box)
        return row

    def _album_row(self, album):
        row = Gtk.ListBoxRow()
        row.album = album
        row.result_type = "album"

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(9)
        box.set_margin_end(9)

        image = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        image.set_pixel_size(34)
        image.add_css_class("album-cover")
        if album.props.thumbnail:
            image.set_from_file(album.props.thumbnail)
        box.append(image)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        title = Gtk.Label(label=album.props.title, xalign=0)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(title)
        summary = Gtk.Label(label=album.props.artist, xalign=0)
        summary.set_ellipsize(Pango.EllipsizeMode.END)
        summary.add_css_class("caption")
        summary.add_css_class("dim-label")
        labels.append(summary)
        box.append(labels)

        row.set_child(box)
        return row

    def _on_row_activated(self, _listbox, row):
        result_type = getattr(row, "result_type", None)
        if result_type == "artist":
            self._play_artist(row.artist)
            return
        if result_type == "album":
            self._play_album(row.album)
            return

        song = getattr(row, "song", None)
        if song:
            self._play_song(song)

    def _play_song(self, song):
        songs_model = self._library.search(self._entry.get_text().strip())
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _play_album(self, album):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_artist(self, artist):
        songs_model = self._library.get_songs_for_artist(artist.props.name)
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)
