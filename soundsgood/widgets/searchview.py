# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango

from soundsgood.widgets.playlistcontextmenu import PlaylistContextMenu
from soundsgood.widgets.songrow import format_duration, set_accessible_label


class SearchResult(GObject.GObject):
    """Presentation entry consumed by the virtualized search list."""

    kind = GObject.Property(type=str, default="song")
    item = GObject.Property(type=object, default=None)
    title = GObject.Property(type=str, default="")
    subtitle = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SearchResultItem(Gtk.Stack):
    def __init__(self, application, on_add):
        super().__init__()
        self._app = application
        self._on_add = on_add
        self._entry = None

        self._section = Gtk.Label(xalign=0)
        self._section.add_css_class("title-4")
        self._section.add_css_class("search-section")
        self.add_named(self._section, "section")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.add_css_class("search-result")
        self._image = Gtk.Image(icon_name="audio-x-generic-symbolic")
        self._image.set_pixel_size(38)
        row.append(self._image)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._title = Gtk.Label(xalign=0)
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        self._title.add_css_class("song-title")
        labels.append(self._title)
        self._subtitle = Gtk.Label(xalign=0)
        self._subtitle.set_ellipsize(Pango.EllipsizeMode.END)
        self._subtitle.add_css_class("caption")
        self._subtitle.add_css_class("dim-label")
        labels.append(self._subtitle)
        row.append(labels)

        self._duration = Gtk.Label(width_chars=6)
        self._duration.add_css_class("dim-label")
        self._duration.add_css_class("song-duration")
        row.append(self._duration)

        self._add = Gtk.Button(icon_name="list-add-symbolic")
        self._add.add_css_class("flat")
        self._add.add_css_class("compact-icon")
        self._add.set_valign(Gtk.Align.CENTER)
        self._add.set_tooltip_text(_("Add to playlist"))
        set_accessible_label(self._add, _("Add to playlist"))
        self._add.connect("clicked", self._add_clicked)
        row.append(self._add)
        self.add_named(row, "result")

        self._playlist_menu = PlaylistContextMenu(
            row,
            application,
            self._songs,
            description_provider=self._playlist_description,
        )

    def bind(self, entry):
        self._entry = entry
        if entry.props.kind == "section":
            self._section.set_label(entry.props.title)
            self.set_visible_child_name("section")
            set_accessible_label(self, entry.props.title)
            return

        item = entry.props.item
        self._title.set_label(entry.props.title)
        self._subtitle.set_label(entry.props.subtitle)
        self._duration.set_visible(entry.props.kind == "song")
        self._duration.set_label(
            format_duration(item.props.duration)
            if entry.props.kind == "song"
            else ""
        )
        if entry.props.kind == "artist":
            self._image.set_from_icon_name("avatar-default-symbolic")
            self._image.add_css_class("artist-avatar")
            self._image.remove_css_class("album-cover")
        else:
            self._image.remove_css_class("artist-avatar")
            self._image.add_css_class("album-cover")
            if item.props.thumbnail:
                self._image.set_from_file(item.props.thumbnail)
            else:
                self._image.set_from_icon_name(
                    "media-optical-cd-audio-symbolic"
                    if entry.props.kind == "album"
                    else "audio-x-generic-symbolic"
                )
        self.set_visible_child_name("result")
        set_accessible_label(self, entry.props.title)

    def unbind(self):
        self._entry = None

    def _add_clicked(self, _button):
        if self._entry is not None:
            self._on_add(self._entry)

    def _songs(self):
        if self._entry is None or self._entry.props.kind == "section":
            return []
        item = self._entry.props.item
        if self._entry.props.kind == "song":
            return [item]
        if self._entry.props.kind == "album":
            return [
                item.props.songs.get_item(index)
                for index in range(item.props.songs.get_n_items())
            ]
        songs = self._app.props.library.get_songs_for_artist(item.props.name)
        return [songs.get_item(index) for index in range(songs.get_n_items())]

    def _playlist_description(self):
        if self._entry is None:
            return ""
        return _("Add %s to a saved playlist") % self._entry.props.title


def create_search_factory(application, on_add):
    factory = Gtk.SignalListItemFactory()
    factory.connect(
        "setup",
        lambda _factory, item: item.set_child(SearchResultItem(application, on_add)),
    )
    factory.connect(
        "bind",
        lambda _factory, item: item.get_child().bind(item.get_item()),
    )
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


class SearchView(Adw.Bin):
    """Contextual, virtualized global library search."""

    def __init__(self, application, on_close=None):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._on_close = on_close
        self._search_source_id = 0
        self._last_song_results = []

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.add_css_class("page-toolbar")
        close = Gtk.Button(icon_name="go-previous-symbolic")
        close.add_css_class("flat")
        close.add_css_class("compact-icon")
        close.set_tooltip_text(_("Close search"))
        set_accessible_label(close, _("Close search"))
        close.connect("clicked", lambda *_args: self.close())
        search_box.append(close)

        self._entry = Gtk.SearchEntry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text(_("Search songs, albums, artists..."))
        self._entry.connect("search-changed", self._on_search_changed)
        search_box.append(self._entry)
        self._add_results = Gtk.Button(icon_name="list-add-symbolic")
        self._add_results.add_css_class("flat")
        self._add_results.add_css_class("compact-icon")
        self._add_results.set_tooltip_text(_("Add song results to playlist"))
        set_accessible_label(self._add_results, _("Add song results to playlist"))
        self._add_results.connect("clicked", self._add_search_results)
        self._add_results.set_visible(False)
        search_box.append(self._add_results)
        box.append(search_box)

        self._model = Gio.ListStore(item_type=SearchResult)
        selection = Gtk.NoSelection.new(self._model)
        self._results = Gtk.ListView.new(
            selection,
            create_search_factory(application, self._add_entry),
        )
        self._results.add_css_class("library-list")
        self._results.set_single_click_activate(False)
        self._results.connect("activate", self._on_result_activated)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._results)

        self._status = Adw.StatusPage()
        self._status.add_css_class("compact")
        self._status.add_css_class("visual-status")
        self._status.set_icon_name("system-search-symbolic")
        self._status.set_title(_("Search your music"))
        self._status.set_description(
            _("Find songs, albums, and artists in your local library.")
        )

        self._content = Gtk.Stack()
        self._content.set_vexpand(True)
        self._content.add_named(self._status, "status")
        self._content.add_named(scrolled, "results")
        box.append(self._content)
        self.set_child(box)

    def grab_search_focus(self):
        self._entry.grab_focus()

    def close(self):
        if self._on_close:
            self._on_close()

    def _on_search_changed(self, entry):
        if self._search_source_id:
            GLib.source_remove(self._search_source_id)
        query = entry.get_text().strip()
        self._search_source_id = GLib.timeout_add(180, self._run_search, query)

    def _run_search(self, query):
        self._search_source_id = 0
        self._model.remove_all()
        self._last_song_results = []
        self._add_results.set_visible(False)
        if not query:
            self._status.set_title(_("Search your music"))
            self._status.set_description(
                _("Find songs, albums, and artists in your local library.")
            )
            self._content.set_visible_child_name("status")
            return GLib.SOURCE_REMOVE

        songs = self._library.search(query)
        albums = self._library.search_albums(query)
        artists = self._library.search_artists(query)
        self._last_song_results = [
            songs.get_item(index) for index in range(songs.get_n_items())
        ]

        if artists:
            self._append_section(_("Artists"))
            for artist in artists[:20]:
                self._model.append(
                    SearchResult(
                        kind="artist",
                        item=artist,
                        title=artist.props.name,
                        subtitle=_("%d albums, %d songs")
                        % (artist.props.album_count, artist.props.song_count),
                    )
                )
        if albums:
            self._append_section(_("Albums"))
            for album in albums[:30]:
                self._model.append(
                    SearchResult(
                        kind="album",
                        item=album,
                        title=album.props.title,
                        subtitle=album.props.artist,
                    )
                )
        if self._last_song_results:
            self._append_section(_("Songs"))
            for song in self._last_song_results[:100]:
                self._model.append(
                    SearchResult(
                        kind="song",
                        item=song,
                        title=song.props.title,
                        subtitle=f"{song.props.artist} — {song.props.album}",
                    )
                )

        self._add_results.set_visible(bool(self._last_song_results))
        if self._model.get_n_items():
            self._content.set_visible_child_name("results")
        else:
            self._status.set_title(_("No results"))
            self._status.set_description(
                _("Try a different title, album, artist, genre, or year.")
            )
            self._content.set_visible_child_name("status")
        return GLib.SOURCE_REMOVE

    def do_unroot(self):
        if self._search_source_id:
            GLib.source_remove(self._search_source_id)
            self._search_source_id = 0
        Adw.Bin.do_unroot(self)

    def _append_section(self, title):
        self._model.append(SearchResult(kind="section", title=title))

    def _on_result_activated(self, _listview, position):
        entry = self._model.get_item(position)
        if entry is None or entry.props.kind == "section":
            return
        if entry.props.kind == "song":
            self._play_song(entry.props.item)
        elif entry.props.kind == "album":
            self._play_album(entry.props.item)
        else:
            self._play_artist(entry.props.item)

    def _add_entry(self, entry):
        item = entry.props.item
        if entry.props.kind == "song":
            songs = [item]
        elif entry.props.kind == "album":
            songs = [
                item.props.songs.get_item(index)
                for index in range(item.props.songs.get_n_items())
            ]
        else:
            model = self._library.get_songs_for_artist(item.props.name)
            songs = [model.get_item(index) for index in range(model.get_n_items())]
        self._app.add_to_playlist(
            songs,
            self.get_root(),
            _("Add %s to a saved playlist") % entry.props.title,
        )

    def _play_song(self, song):
        songs = self._library.search(self._entry.get_text().strip())
        queue = [songs.get_item(index) for index in range(songs.get_n_items())]
        self._player.play_song(song, queue)

    def _add_search_results(self, _button):
        if self._last_song_results:
            self._app.add_to_playlist(
                self._last_song_results,
                self.get_root(),
                _("Add %d search results to a saved playlist")
                % len(self._last_song_results),
            )

    def _play_album(self, album):
        songs = [
            album.props.songs.get_item(index)
            for index in range(album.props.songs.get_n_items())
        ]
        if songs:
            self._player.play_song(songs[0], songs)

    def _play_artist(self, artist):
        model = self._library.get_songs_for_artist(artist.props.name)
        songs = [model.get_item(index) for index in range(model.get_n_items())]
        if songs:
            self._player.play_song(songs[0], songs)
