# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Pango

from soundsgood.models import LibraryState
from soundsgood.widgets.songrow import SongRow, set_accessible_label


class AlbumsView(Adw.Bin):
    """Grid of albums."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_min_children_per_line(1)
        self._flowbox.set_max_children_per_line(8)
        self._flowbox.set_column_spacing(12)
        self._flowbox.set_row_spacing(18)
        self._flowbox.set_margin_top(18)
        self._flowbox.set_margin_bottom(18)
        self._flowbox.set_margin_start(18)
        self._flowbox.set_margin_end(18)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._flowbox)
        self._stack.add_named(scrolled, "grid")

        self._album_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._album_page.set_margin_top(18)
        self._album_page.set_margin_bottom(18)
        self._album_page.set_margin_start(18)
        self._album_page.set_margin_end(18)

        detail_scrolled = Gtk.ScrolledWindow()
        detail_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        detail_scrolled.set_child(self._album_page)
        self._stack.add_named(detail_scrolled, "album")
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

    def _rebuild(self):
        self._clear()
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        albums = self._library.props.albums
        if albums.get_n_items() == 0:
            self._flowbox.append(self._placeholder(self._library.props.status_message or _("No albums found")))
            return

        for index in range(albums.get_n_items()):
            album = albums.get_item(index)
            self._flowbox.append(self._album_button(album))

    def _show_status(self):
        self._clear()
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No albums found")
        self._flowbox.append(
            self._placeholder(
                message,
                show_button=self._library.props.scan_state != int(LibraryState.SCANNING),
            )
        )

    def _album_button(self, album):
        button = Gtk.Button()
        button.add_css_class("flat")
        button.album = album
        button.set_tooltip_text(_("Open album"))
        set_accessible_label(button, _("Open album"))
        button.connect("clicked", self._on_album_clicked)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(170, -1)

        cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        cover.set_pixel_size(96)
        if album.props.thumbnail:
            cover.set_from_file(album.props.thumbnail)
        cover.add_css_class("album-cover")
        box.append(cover)

        title = Gtk.Label(label=album.props.title)
        title.set_wrap(True)
        title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(22)
        title.add_css_class("heading")
        box.append(title)

        artist = Gtk.Label(label=album.props.artist)
        artist.set_ellipsize(Pango.EllipsizeMode.END)
        artist.set_max_width_chars(22)
        artist.add_css_class("dim-label")
        box.append(artist)

        count = Gtk.Label(label=_("%d songs") % album.props.song_count)
        count.add_css_class("caption")
        count.add_css_class("dim-label")
        box.append(count)

        button.set_child(box)
        return button

    def _placeholder(self, text: str, show_button: bool = True):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(48)
        box.set_halign(Gtk.Align.CENTER)

        label = Gtk.Label(label=text)
        label.add_css_class("dim-label")
        box.append(label)

        if show_button:
            button = Gtk.Button(label=_("Choose Music Folder"))
            button.set_icon_name("folder-music-symbolic")
            button.add_css_class("suggested-action")
            button.connect("clicked", self._on_choose_folder_clicked)
            set_accessible_label(button, _("Choose Music Folder"))
            box.append(button)

        return box

    def _clear(self):
        child = self._flowbox.get_first_child()
        while child:
            self._flowbox.remove(child)
            child = self._flowbox.get_first_child()

    def _on_album_clicked(self, button):
        self._show_album(button.album)

    def _on_choose_folder_clicked(self, _button):
        self._app.select_music_folder(self.get_root())

    def _show_album(self, album):
        self._clear_box(self._album_page)

        back_button = Gtk.Button(icon_name="go-previous-symbolic")
        back_button.set_tooltip_text(_("Back to albums"))
        set_accessible_label(back_button, _("Back to albums"))
        back_button.set_halign(Gtk.Align.START)
        back_button.connect("clicked", lambda *_: self._stack.set_visible_child_name("grid"))
        self._album_page.append(back_button)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        header.set_valign(Gtk.Align.START)

        cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        cover.set_pixel_size(180)
        if album.props.thumbnail:
            cover.set_from_file(album.props.thumbnail)
        header.append(cover)

        metadata = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        metadata.set_valign(Gtk.Align.CENTER)
        metadata.set_hexpand(True)
        title = Gtk.Label(label=album.props.title, xalign=0)
        title.set_wrap(True)
        title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title.add_css_class("title-1")
        metadata.append(title)

        artist = Gtk.Label(label=album.props.artist, xalign=0)
        artist.set_wrap(True)
        artist.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        artist.add_css_class("heading")
        artist.add_css_class("dim-label")
        metadata.append(artist)

        details = []
        if album.props.year:
            details.append(album.props.year)
        details.append(_("%d songs") % album.props.song_count)
        summary = Gtk.Label(label=" - ".join(details), xalign=0)
        summary.add_css_class("dim-label")
        metadata.append(summary)

        play_button = Gtk.Button(label=_("Play"))
        play_button.set_icon_name("media-playback-start-symbolic")
        set_accessible_label(play_button, _("Play album"))
        play_button.add_css_class("suggested-action")
        play_button.set_halign(Gtk.Align.START)
        play_button.connect("clicked", lambda *_: self._play_album(album))
        metadata.append(play_button)

        header.append(metadata)
        self._album_page.append(header)

        songs_list = Gtk.ListBox()
        songs_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        songs_list.set_activate_on_single_click(False)
        songs_list.connect("row-activated", self._on_album_song_activated)
        songs_list.album = album

        self._append_song_rows(songs_list, album)

        self._album_page.append(songs_list)
        self._stack.set_visible_child_name("album")

    def _play_album(self, album):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_album_song(self, album, song):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _on_album_song_activated(self, _listbox, row):
        song = getattr(row, "song", None)
        album = getattr(_listbox, "album", None)
        if song and album:
            self._play_album_song(album, song)

    def _append_song_rows(self, songs_list, album):
        songs_model = album.props.songs
        show_disc_headers = self._should_show_disc_headers(songs_model)
        current_disc = None
        for index in range(songs_model.get_n_items()):
            song = songs_model.get_item(index)
            disc_number = song.props.disc_number or 1
            if show_disc_headers and disc_number != current_disc:
                songs_list.append(self._disc_header(disc_number))
                current_disc = disc_number

            songs_list.append(
                SongRow(
                    song,
                    show_context=False,
                    player=self._player,
                    on_activate=lambda selected, current_album=album: self._play_album_song(
                        current_album,
                        selected,
                    ),
                )
            )

    def _should_show_disc_headers(self, songs_model) -> bool:
        discs = {
            songs_model.get_item(index).props.disc_number or 1
            for index in range(songs_model.get_n_items())
        }
        return len(discs) > 1 or any(disc > 1 for disc in discs)

    def _disc_header(self, disc_number: int):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        label = Gtk.Label(label=_("Disc %d") % disc_number, xalign=0)
        label.add_css_class("heading")
        label.add_css_class("dim-label")
        label.set_margin_top(12)
        label.set_margin_bottom(6)
        label.set_margin_start(12)
        label.set_margin_end(12)
        row.set_child(label)
        return row

    def _clear_box(self, box):
        child = box.get_first_child()
        while child:
            box.remove(child)
            child = box.get_first_child()
