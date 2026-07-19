# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk, Pango

from soundsgood.models import LibraryState
from soundsgood.widgets.detailrow import DetailEntry, create_detail_factory
from soundsgood.widgets.songrow import set_accessible_label


class AlbumTile(Gtk.Box):
    """Reusable grid tile bound by Gtk.GridView's item factory."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self._album = None
        self._album_handlers = []
        self.add_css_class("album-tile")
        self.set_size_request(120, -1)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(4)
        self.set_margin_end(4)

        self._cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        self._cover.set_pixel_size(104)
        self._cover.add_css_class("album-cover")
        self.append(self._cover)

        self._title = Gtk.Label()
        self._title.set_wrap(True)
        self._title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        self._title.set_lines(2)
        self._title.add_css_class("heading")
        self.append(self._title)

        self._artist = Gtk.Label()
        self._artist.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist.add_css_class("dim-label")
        self.append(self._artist)

        self._count = Gtk.Label()
        self._count.add_css_class("caption")
        self._count.add_css_class("dim-label")
        self.append(self._count)

    def bind(self, album):
        self.unbind()
        self._album = album
        self._album_handlers = [
            album.connect(f"notify::{prop}", self._sync)
            for prop in ("thumbnail", "title", "artist", "song-count")
        ]
        self._sync()

    def unbind(self):
        if self._album is not None:
            for handler_id in self._album_handlers:
                if self._album.handler_is_connected(handler_id):
                    self._album.disconnect(handler_id)
        self._album_handlers.clear()
        self._album = None

    def _sync(self, *_args):
        if self._album is None:
            return
        if self._album.props.thumbnail:
            self._cover.set_from_file(self._album.props.thumbnail)
        else:
            self._cover.set_from_icon_name("media-optical-cd-audio-symbolic")
        self._title.set_label(self._album.props.title)
        self._artist.set_label(self._album.props.artist)
        self._count.set_label(_("%d songs") % self._album.props.song_count)
        set_accessible_label(self, _("Open album %s") % self._album.props.title)


def create_album_factory():
    factory = Gtk.SignalListItemFactory()
    factory.connect("setup", lambda _factory, item: item.set_child(AlbumTile()))
    factory.connect(
        "bind",
        lambda _factory, item: item.get_child().bind(item.get_item()),
    )
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


class AlbumsView(Adw.Bin):
    """Grid of albums."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._compact = False
        self._selected_album = None

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self._album_selection = Gtk.NoSelection.new(self._library.props.albums)
        self._grid = Gtk.GridView.new(self._album_selection, create_album_factory())
        self._grid.set_min_columns(1)
        self._grid.set_max_columns(8)
        self._grid.set_single_click_activate(True)
        self._grid.connect("activate", self._on_album_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._grid)

        self._grid_stack = Gtk.Stack()
        self._grid_stack.add_named(scrolled, "albums")
        self._status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._status_box.set_halign(Gtk.Align.CENTER)
        self._status_box.set_valign(Gtk.Align.CENTER)
        self._status_label = Gtk.Label()
        self._status_label.add_css_class("dim-label")
        self._status_box.append(self._status_label)
        self._status_button = Gtk.Button(label=_("Choose Music Folder"))
        self._status_button.set_icon_name("folder-music-symbolic")
        self._status_button.add_css_class("suggested-action")
        self._status_button.add_css_class("compact-pill")
        self._status_button.connect("clicked", self._on_choose_folder_clicked)
        set_accessible_label(self._status_button, _("Choose Music Folder"))
        self._status_box.append(self._status_button)
        self._grid_stack.add_named(self._status_box, "status")
        self._stack.add_named(self._grid_stack, "grid")

        self._album_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self._album_page.set_margin_top(14)
        self._album_page.set_margin_bottom(14)
        self._album_page.set_margin_start(14)
        self._album_page.set_margin_end(14)

        self._stack.add_named(self._album_page, "album")
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
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        albums = self._library.props.albums
        if albums.get_n_items() == 0:
            self._status_label.set_label(
                self._library.props.status_message or _("No albums found")
            )
            self._status_button.set_visible(True)
            self._grid_stack.set_visible_child_name("status")
            return
        self._grid_stack.set_visible_child_name("albums")

    def _show_status(self):
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No albums found")
        self._status_label.set_label(message)
        self._status_button.set_visible(
            self._library.props.scan_state != int(LibraryState.SCANNING)
        )
        self._grid_stack.set_visible_child_name("status")

    def _on_album_activated(self, _grid, position):
        album = self._library.props.albums.get_item(position)
        if album is not None:
            self._show_album(album)

    def _on_choose_folder_clicked(self, _button):
        self._app.select_music_folder(self.get_root())

    def _show_album(self, album):
        self._clear_box(self._album_page)
        self._selected_album = album

        back_button = Gtk.Button(icon_name="go-previous-symbolic")
        back_button.add_css_class("flat")
        back_button.add_css_class("compact-icon")
        back_button.set_tooltip_text(_("Back to albums"))
        set_accessible_label(back_button, _("Back to albums"))
        back_button.set_halign(Gtk.Align.START)
        back_button.connect("clicked", lambda *_: self._stack.set_visible_child_name("grid"))
        self._album_page.append(back_button)

        header = Gtk.Box(
            orientation=(
                Gtk.Orientation.VERTICAL
                if self._compact else Gtk.Orientation.HORIZONTAL
            ),
            spacing=14,
        )
        header.add_css_class("detail-header")
        header.set_valign(Gtk.Align.START)

        cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        cover.set_pixel_size(120 if self._compact else 160)
        cover.add_css_class("album-cover")
        if album.props.thumbnail:
            cover.set_from_file(album.props.thumbnail)
        header.append(cover)

        metadata = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        metadata.set_valign(Gtk.Align.CENTER)
        metadata.set_hexpand(True)
        title = Gtk.Label(label=album.props.title, xalign=0)
        title.set_wrap(True)
        title.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title.add_css_class("title-2")
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
        play_button.add_css_class("compact-pill")
        play_button.set_halign(Gtk.Align.START)
        play_button.connect("clicked", lambda *_: self._play_album(album))
        metadata.append(play_button)

        header.append(metadata)
        self._album_page.append(header)

        self._album_song_model = self._build_song_model(album)
        selection = Gtk.NoSelection.new(self._album_song_model)
        songs_list = Gtk.ListView.new(
            selection,
            create_detail_factory(
                self._player,
                self._play_album,
                self._play_album_song,
            ),
        )
        songs_list.add_css_class("boxed-list")
        songs_list.set_single_click_activate(False)
        songs_list.connect("activate", self._on_album_song_activated)
        songs_scroller = Gtk.ScrolledWindow()
        songs_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        songs_scroller.set_vexpand(True)
        songs_scroller.set_child(songs_list)
        self._album_page.append(songs_scroller)
        self._stack.set_visible_child_name("album")

    def set_compact(self, compact: bool):
        if self._compact == compact:
            return
        self._compact = compact
        if self._selected_album is not None and self._stack.get_visible_child_name() == "album":
            self._show_album(self._selected_album)

    def _play_album(self, album):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_album_song(self, album, song):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _on_album_song_activated(self, _listview, position):
        entry = self._album_song_model.get_item(position)
        if entry and entry.props.kind == "song":
            self._play_album_song(entry.props.context, entry.props.item)

    def _build_song_model(self, album):
        model = Gio.ListStore(item_type=DetailEntry)
        songs_model = album.props.songs
        show_disc_headers = self._should_show_disc_headers(songs_model)
        current_disc = None
        for index in range(songs_model.get_n_items()):
            song = songs_model.get_item(index)
            disc_number = song.props.disc_number or 1
            if show_disc_headers and disc_number != current_disc:
                model.append(
                    DetailEntry(kind="heading", title=_("Disc %d") % disc_number)
                )
                current_disc = disc_number
            model.append(
                DetailEntry(kind="song", item=song, context=album)
            )
        return model

    def _should_show_disc_headers(self, songs_model) -> bool:
        discs = {
            songs_model.get_item(index).props.disc_number or 1
            for index in range(songs_model.get_n_items())
        }
        return len(discs) > 1 or any(disc > 1 for disc in discs)

    def _clear_box(self, box):
        child = box.get_first_child()
        while child:
            box.remove(child)
            child = box.get_first_child()
