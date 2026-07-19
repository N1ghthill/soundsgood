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


class ArtistListItem(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        self._artist = None
        self._artist_handlers = []
        self.add_css_class("song-item")
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(9)
        self.set_margin_end(9)
        image = Gtk.Image(icon_name="avatar-default-symbolic")
        image.set_pixel_size(28)
        image.add_css_class("artist-avatar")
        self.append(image)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._name = Gtk.Label(xalign=0)
        self._name.set_ellipsize(Pango.EllipsizeMode.END)
        self._name.add_css_class("heading")
        labels.append(self._name)
        self._summary = Gtk.Label(xalign=0)
        self._summary.add_css_class("caption")
        self._summary.add_css_class("dim-label")
        labels.append(self._summary)
        self.append(labels)

    def bind(self, artist):
        self.unbind()
        self._artist = artist
        self._artist_handlers = [
            artist.connect(f"notify::{prop}", self._sync)
            for prop in ("name", "album-count", "song-count")
        ]
        self._sync()

    def unbind(self):
        if self._artist is not None:
            for handler_id in self._artist_handlers:
                if self._artist.handler_is_connected(handler_id):
                    self._artist.disconnect(handler_id)
        self._artist_handlers.clear()
        self._artist = None

    def _sync(self, *_args):
        if self._artist is None:
            return
        self._name.set_label(self._artist.props.name)
        self._summary.set_label(
            _("%d albums, %d songs")
            % (self._artist.props.album_count, self._artist.props.song_count)
        )


def create_artist_factory():
    factory = Gtk.SignalListItemFactory()
    factory.connect("setup", lambda _factory, item: item.set_child(ArtistListItem()))
    factory.connect(
        "bind",
        lambda _factory, item: item.get_child().bind(item.get_item()),
    )
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


class ArtistsView(Adw.Bin):
    """Artists browser with songs for the selected artist."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._selected_artist = None
        self._compact = False

        self._split_view = Adw.NavigationSplitView()

        self._artist_selection = Gtk.SingleSelection.new(self._library.props.artists)
        self._artist_selection.set_autoselect(False)
        self._artist_selection.set_can_unselect(True)
        self._artist_selection.connect(
            "notify::selected-item",
            self._on_artist_selection_changed,
        )
        self._artists_list = Gtk.ListView.new(
            self._artist_selection,
            create_artist_factory(),
        )
        self._artists_list.set_single_click_activate(True)

        artists_scroll = Gtk.ScrolledWindow()
        artists_scroll.set_child(self._artists_list)

        self._sidebar_stack = Gtk.Stack()
        self._sidebar_stack.add_named(artists_scroll, "artists")
        self._sidebar_status = Gtk.Label()
        self._sidebar_status.set_wrap(True)
        self._sidebar_status.set_halign(Gtk.Align.CENTER)
        self._sidebar_status.set_valign(Gtk.Align.CENTER)
        self._sidebar_status.set_margin_start(18)
        self._sidebar_status.set_margin_end(18)
        self._sidebar_status.add_css_class("dim-label")
        self._sidebar_stack.add_named(self._sidebar_status, "status")
        sidebar_page = Adw.NavigationPage.new(self._sidebar_stack, _("Artists"))

        self._artist_detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self._artist_detail.set_margin_top(14)
        self._artist_detail.set_margin_bottom(14)
        self._artist_detail.set_margin_start(14)
        self._artist_detail.set_margin_end(14)

        content_page = Adw.NavigationPage.new(self._artist_detail, _("Artist"))

        self._split_view.set_sidebar(sidebar_page)
        self._split_view.set_content(content_page)
        self.set_child(self._split_view)

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
        self._clear_box(self._artist_detail)
        message = self._library.props.status_message
        if not message and self._library.props.scan_state == int(LibraryState.SCANNING):
            message = _("Scanning music...")
        elif not message:
            message = _("No artists found")
        self._sidebar_status.set_label(message)
        self._sidebar_stack.set_visible_child_name("status")

    def _rebuild(self):
        self._clear_box(self._artist_detail)
        if self._library.props.scan_state == int(LibraryState.ERROR):
            self._show_status()
            return

        artists = self._library.props.artists
        if artists.get_n_items() == 0:
            self._sidebar_status.set_label(
                self._library.props.status_message or _("No artists found")
            )
            self._sidebar_stack.set_visible_child_name("status")
            return
        self._sidebar_stack.set_visible_child_name("artists")
        self._artist_selection.set_selected(0)
        artist = self._artist_selection.get_selected_item()
        if artist is not None:
            self._show_artist_songs(artist)

    def _show_artist_songs(self, artist):
        self._clear_box(self._artist_detail)
        self._selected_artist = artist

        if self._compact:
            back_button = Gtk.Button(icon_name="go-previous-symbolic")
            back_button.add_css_class("flat")
            back_button.add_css_class("compact-icon")
            back_button.set_halign(Gtk.Align.START)
            back_button.set_tooltip_text(_("Back to artists"))
            set_accessible_label(back_button, _("Back to artists"))
            back_button.connect(
                "clicked",
                lambda *_args: self._split_view.set_show_content(False),
            )
            self._artist_detail.append(back_button)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        header.add_css_class("detail-header")
        header.set_valign(Gtk.Align.START)

        image = Gtk.Image(icon_name="avatar-default-symbolic")
        image.set_pixel_size(72)
        image.add_css_class("artist-avatar")
        header.append(image)

        metadata = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        metadata.set_valign(Gtk.Align.CENTER)
        metadata.set_hexpand(True)
        name = Gtk.Label(label=artist.props.name, xalign=0)
        name.set_wrap(True)
        name.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        name.add_css_class("title-2")
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
        set_accessible_label(play_button, _("Play artist"))
        play_button.add_css_class("suggested-action")
        play_button.add_css_class("compact-pill")
        play_button.set_halign(Gtk.Align.START)
        play_button.connect("clicked", lambda *_: self._play_artist())
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.append(play_button)
        add_button = Gtk.Button(icon_name="list-add-symbolic")
        add_button.add_css_class("flat")
        add_button.add_css_class("compact-icon")
        add_button.set_valign(Gtk.Align.CENTER)
        add_button.set_tooltip_text(_("Add artist to playlist"))
        set_accessible_label(add_button, _("Add artist to playlist"))
        add_button.connect("clicked", lambda *_: self._add_artist())
        actions.append(add_button)
        metadata.append(actions)

        header.append(metadata)
        self._artist_detail.append(header)

        albums = self._library.get_albums_for_artist(artist.props.name)
        if not albums:
            self._artist_detail.append(self._placeholder(_("No songs found"), show_button=False))
            return

        self._artist_song_model = self._build_artist_model(albums, artist.props.name)
        selection = Gtk.NoSelection.new(self._artist_song_model)
        songs_list = Gtk.ListView.new(
            selection,
            create_detail_factory(
                self._player,
                self._play_album,
                self._play_album_song,
                self._add_song,
            ),
        )
        songs_list.set_single_click_activate(False)
        songs_list.connect("activate", self._on_artist_song_activated)
        songs_scroller = Gtk.ScrolledWindow()
        songs_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        songs_scroller.set_vexpand(True)
        songs_scroller.set_child(songs_list)
        self._artist_detail.append(songs_scroller)

    def _build_artist_model(self, albums, artist_name):
        model = Gio.ListStore(item_type=DetailEntry)
        for album in albums:
            details = []
            if album.props.year:
                details.append(album.props.year)
            details.append(_("%d songs") % album.props.song_count)
            model.append(
                DetailEntry(
                    kind="album",
                    item=album,
                    title=album.props.title,
                    subtitle=" - ".join(details),
                )
            )
            songs_model = album.props.songs
            show_disc_headers = self._should_show_disc_headers(
                songs_model, album, artist_name
            )
            current_disc = None
            for index in range(songs_model.get_n_items()):
                song = songs_model.get_item(index)
                if song.props.artist != artist_name and album.props.artist != artist_name:
                    continue
                disc_number = song.props.disc_number or 1
                if show_disc_headers and disc_number != current_disc:
                    model.append(
                        DetailEntry(
                            kind="heading",
                            title=_("Disc %d") % disc_number,
                        )
                    )
                    current_disc = disc_number
                model.append(DetailEntry(kind="song", item=song, context=album))
        return model

    def _should_show_disc_headers(self, songs_model, album, artist_name) -> bool:
        discs = set()
        for index in range(songs_model.get_n_items()):
            song = songs_model.get_item(index)
            if song.props.artist != artist_name and album.props.artist != artist_name:
                continue
            discs.add(song.props.disc_number or 1)
        return len(discs) > 1 or any(disc > 1 for disc in discs)

    def _placeholder(self, text, show_button: bool = True):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_halign(Gtk.Align.CENTER)

        label = Gtk.Label(label=text)
        label.add_css_class("dim-label")
        box.append(label)

        if show_button:
            button = Gtk.Button(label=_("Choose Music Folder"))
            button.set_icon_name("folder-music-symbolic")
            button.add_css_class("suggested-action")
            button.add_css_class("compact-pill")
            button.connect("clicked", self._on_choose_folder_clicked)
            set_accessible_label(button, _("Choose Music Folder"))
            box.append(button)

        return box

    def _clear_box(self, box):
        child = box.get_first_child()
        while child:
            box.remove(child)
            child = box.get_first_child()

    def _on_artist_selection_changed(self, selection, _pspec):
        artist = selection.get_selected_item()
        if artist is None:
            return
        self._show_artist_songs(artist)
        if self._compact:
            self._split_view.set_show_content(True)

    def set_compact(self, compact: bool):
        if self._compact == compact:
            return
        self._compact = compact
        self._split_view.set_collapsed(compact)
        if not compact:
            self._split_view.set_show_content(True)
        elif self._selected_artist is None:
            self._split_view.set_show_content(False)
        if self._selected_artist is not None:
            self._show_artist_songs(self._selected_artist)

    def _play_artist(self):
        if self._selected_artist is None:
            return

        songs_model = self._library.get_songs_for_artist(self._selected_artist.props.name)
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _add_artist(self):
        if self._selected_artist is None:
            return
        songs_model = self._library.get_songs_for_artist(self._selected_artist.props.name)
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._app.add_to_playlist(
            songs,
            self.get_root(),
            _("Add artist %s to a saved playlist") % self._selected_artist.props.name,
        )

    def _add_song(self, song):
        self._app.add_to_playlist(
            [song],
            self.get_root(),
            _("Add %s to a saved playlist") % song.props.title,
        )

    def _play_album(self, album):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_album_song(self, album, song):
        songs_model = album.props.songs
        songs = [songs_model.get_item(i) for i in range(songs_model.get_n_items())]
        self._player.play_song(song, songs)

    def _on_artist_song_activated(self, _listview, position):
        entry = self._artist_song_model.get_item(position)
        if entry and entry.props.kind == "song":
            self._play_album_song(entry.props.context, entry.props.item)

    def _on_choose_folder_clicked(self, _button):
        self._app.select_music_folder(self.get_root())
