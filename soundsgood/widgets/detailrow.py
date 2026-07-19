# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Factory-backed rows shared by album and artist detail views."""

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk, Pango

from soundsgood.widgets.songrow import SongListItem, set_accessible_label
from soundsgood.widgets.playlistcontextmenu import PlaylistContextMenu


class DetailEntry(GObject.GObject):
    """Typed model entry for an album heading, disc heading, or song."""

    kind = GObject.Property(type=str, default="song")
    item = GObject.Property(type=object, default=None)
    context = GObject.Property(type=object, default=None)
    title = GObject.Property(type=str, default="")
    subtitle = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self.props, key, value)


class DetailListItem(Gtk.Stack):
    """Reusable detail row whose visible content follows its model entry."""

    def __init__(
        self,
        player,
        on_play_album,
        on_play_song,
        on_add_song=None,
        application=None,
    ):
        super().__init__()
        self._entry = None
        self._on_play_album = on_play_album
        self._on_play_song = on_play_song

        album_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        album_box.add_css_class("section-header")
        album_box.set_margin_top(8)
        album_box.set_margin_bottom(4)
        album_box.set_margin_start(4)
        album_box.set_margin_end(4)
        self._album_cover = Gtk.Image(icon_name="media-optical-cd-audio-symbolic")
        self._album_cover.set_pixel_size(48)
        self._album_cover.add_css_class("album-cover")
        album_box.append(self._album_cover)
        album_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        album_labels.set_hexpand(True)
        self._album_title = Gtk.Label(xalign=0)
        self._album_title.set_ellipsize(Pango.EllipsizeMode.END)
        self._album_title.add_css_class("title-4")
        album_labels.append(self._album_title)
        self._album_subtitle = Gtk.Label(xalign=0)
        self._album_subtitle.add_css_class("caption")
        self._album_subtitle.add_css_class("dim-label")
        album_labels.append(self._album_subtitle)
        album_box.append(album_labels)
        album_play = Gtk.Button(icon_name="media-playback-start-symbolic")
        album_play.add_css_class("flat")
        album_play.add_css_class("compact-icon")
        album_play.set_valign(Gtk.Align.CENTER)
        album_play.set_tooltip_text("Play album")
        set_accessible_label(album_play, "Play album")
        album_play.connect("clicked", self._play_album)
        album_box.append(album_play)
        self.add_named(album_box, "album")

        self._album_playlist_menu = None
        if application is not None:
            self._album_playlist_menu = PlaylistContextMenu(
                album_box,
                application,
                self._album_songs,
                submenu_label=_("Add Album to Playlist"),
                description_provider=lambda: _("Add album %s to a saved playlist")
                % self._entry.props.title,
            )

        self._heading = Gtk.Label(xalign=0)
        self._heading.add_css_class("heading")
        self._heading.add_css_class("dim-label")
        self._heading.set_margin_top(10)
        self._heading.set_margin_bottom(4)
        self._heading.set_margin_start(10)
        self._heading.set_margin_end(10)
        self.add_named(self._heading, "heading")

        self._song_item = SongListItem(
            player,
            self._play_song,
            False,
            on_add_song,
            application,
        )
        self.add_named(self._song_item, "song")

    def bind(self, entry):
        self.unbind()
        self._entry = entry
        kind = entry.props.kind
        if kind == "album":
            album = entry.props.item
            self._album_title.set_label(entry.props.title)
            self._album_subtitle.set_label(entry.props.subtitle)
            if album and album.props.thumbnail:
                self._album_cover.set_from_file(album.props.thumbnail)
            else:
                self._album_cover.set_from_icon_name("media-optical-cd-audio-symbolic")
            self.set_visible_child_name("album")
        elif kind == "heading":
            self._heading.set_label(entry.props.title)
            self.set_visible_child_name("heading")
        else:
            self._song_item.bind(entry.props.item)
            self.set_visible_child_name("song")

    def unbind(self):
        self._song_item.unbind()
        self._entry = None

    def _play_album(self, _button):
        if self._entry and self._entry.props.kind == "album":
            self._on_play_album(self._entry.props.item)

    def _play_song(self, song):
        if self._entry:
            self._on_play_song(self._entry.props.context, song)

    def _album_songs(self):
        if not self._entry or self._entry.props.kind != "album":
            return []
        album = self._entry.props.item
        songs = album.props.songs
        return [songs.get_item(index) for index in range(songs.get_n_items())]


def create_detail_factory(
    player,
    on_play_album,
    on_play_song,
    on_add_song=None,
    application=None,
):
    factory = Gtk.SignalListItemFactory()

    def setup(_factory, list_item):
        list_item.set_child(
            DetailListItem(
                player,
                on_play_album,
                on_play_song,
                on_add_song,
                application,
            )
        )

    def bind(_factory, list_item):
        list_item.get_child().bind(list_item.get_item())

    def unbind(_factory, list_item):
        list_item.get_child().unbind()

    factory.connect("setup", setup)
    factory.connect("bind", bind)
    factory.connect("unbind", unbind)
    return factory
