# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from soundsgood.models import LibraryState
from soundsgood.widgets.songrow import SongRow


class ArtistsView(Adw.Bin):
    """Artists browser with songs for the selected artist."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._selected_artist = None

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_wide_handle(True)
        paned.set_position(300)

        self._artists_list = Gtk.ListBox()
        self._artists_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._artists_list.connect("row-selected", self._on_artist_selected)

        artists_scroll = Gtk.ScrolledWindow()
        artists_scroll.set_child(self._artists_list)
        paned.set_start_child(artists_scroll)

        self._artist_detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._artist_detail.set_margin_top(18)
        self._artist_detail.set_margin_bottom(18)
        self._artist_detail.set_margin_start(18)
        self._artist_detail.set_margin_end(18)

        songs_scroll = Gtk.ScrolledWindow()
        songs_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        songs_scroll.set_child(self._artist_detail)
        paned.set_end_child(songs_scroll)

        self.set_child(paned)

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
        self._clear(self._artists_list)
        self._clear_box(self._artist_detail)
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No artists found")
        self._artists_list.append(self._placeholder(message))

    def _rebuild(self):
        self._clear(self._artists_list)
        self._clear_box(self._artist_detail)
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        artists = self._library.props.artists
        if artists.get_n_items() == 0:
            self._artists_list.append(self._placeholder(self._library.props.status_message or _("No artists found")))
            return

        for index in range(artists.get_n_items()):
            artist = artists.get_item(index)
            self._artists_list.append(self._artist_row(artist))

        first_row = self._artists_list.get_row_at_index(0)
        if first_row:
            self._artists_list.select_row(first_row)

    def _artist_row(self, artist):
        row = Gtk.ListBoxRow()
        row.artist = artist

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        image = Gtk.Image(icon_name="avatar-default-symbolic")
        image.set_pixel_size(32)
        box.append(image)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name = Gtk.Label(label=artist.props.name, xalign=0)
        name.add_css_class("heading")
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

    def _show_artist_songs(self, artist):
        self._clear_box(self._artist_detail)
        self._selected_artist = artist

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header.set_valign(Gtk.Align.START)

        image = Gtk.Image(icon_name="avatar-default-symbolic")
        image.set_pixel_size(96)
        header.append(image)

        metadata = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        metadata.set_valign(Gtk.Align.CENTER)
        name = Gtk.Label(label=artist.props.name, xalign=0)
        name.add_css_class("title-1")
        metadata.append(name)

        summary = Gtk.Label(
            label=_("%d albums, %d songs") % (
                artist.props.album_count,
                artist.props.song_count,
            ),
            xalign=0,
        )
        summary.add_css_class("dim-label")
        metadata.append(summary)

        play_button = Gtk.Button(label=_("Play"))
        play_button.set_icon_name("media-playback-start-symbolic")
        play_button.add_css_class("suggested-action")
        play_button.set_halign(Gtk.Align.START)
        play_button.connect("clicked", lambda *_: self._play_artist())
        metadata.append(play_button)

        header.append(metadata)
        self._artist_detail.append(header)

        albums = self._library.get_albums_for_artist(artist.props.name)
        if not albums:
            self._artist_detail.append(self._placeholder(_("No songs found")))
            return

        for album in albums:
            self._artist_detail.append(self._album_section(album, artist.props.name))

    def _album_section(self, album, artist_name):
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(12)

        cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        cover.set_pixel_size(64)
        if album.props.thumbnail:
            cover.set_from_file(album.props.thumbnail)
        header.append(cover)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label=album.props.title, xalign=0)
        title.add_css_class("title-4")
        labels.append(title)

        details = []
        if album.props.year:
            details.append(album.props.year)
        details.append(_("%d songs") % album.props.song_count)
        subtitle = Gtk.Label(label=" - ".join(details), xalign=0)
        subtitle.add_css_class("caption")
        subtitle.add_css_class("dim-label")
        labels.append(subtitle)
        header.append(labels)

        play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
        play_button.set_tooltip_text(_("Play album"))
        play_button.set_halign(Gtk.Align.END)
        play_button.set_hexpand(True)
        play_button.connect("clicked", lambda *_: self._play_album(album))
        header.append(play_button)

        section.append(header)

        songs_list = Gtk.ListBox()
        songs_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        songs_list.set_activate_on_single_click(False)
        songs_list.album = album
        songs_list.connect("row-activated", self._on_album_song_activated)

        songs_model = album.props.songs
        for index in range(songs_model.get_n_items()):
            song = songs_model.get_item(index)
            if song.props.artist != artist_name and album.props.artist != artist_name:
                continue

            songs_list.append(
                SongRow(
                    song,
                    show_context=False,
                    on_activate=lambda selected, current_album=album: self._play_album_song(
                        current_album,
                        selected,
                    ),
                    player=self._player,
                )
            )

        section.append(songs_list)
        return section

    def _placeholder(self, text):
        label = Gtk.Label(label=text)
        label.set_margin_top(24)
        label.add_css_class("dim-label")
        return label

    def _clear(self, listbox):
        child = listbox.get_first_child()
        while child:
            listbox.remove(child)
            child = listbox.get_first_child()

    def _clear_box(self, box):
        child = box.get_first_child()
        while child:
            box.remove(child)
            child = box.get_first_child()

    def _on_artist_selected(self, _listbox, row):
        if row and hasattr(row, "artist"):
            self._show_artist_songs(row.artist)

    def _on_song_activated(self, _listbox, row):
        song = getattr(row, "song", None)
        if not song:
            return

        self._play_song(song)

    def _play_song(self, song):
        songs_model = self._library.get_songs_for_artist(self._selected_artist.props.name)
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _play_artist(self):
        if self._selected_artist is None:
            return

        songs_model = self._library.get_songs_for_artist(self._selected_artist.props.name)
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_album(self, album):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_album_song(self, album, song):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _on_album_song_activated(self, listbox, row):
        song = getattr(row, "song", None)
        album = getattr(listbox, "album", None)
        if song and album:
            self._play_album_song(album, song)
