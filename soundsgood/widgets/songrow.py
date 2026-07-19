# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Pango

from soundsgood.models import PlayState


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "--:--"

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def set_accessible_label(widget, label: str):
    try:
        widget.update_property([Gtk.AccessibleProperty.LABEL], [label])
    except (AttributeError, TypeError):
        pass


class SongRow(Gtk.ListBoxRow):
    """Reusable row for a song."""

    def __init__(self, song, show_context: bool = False, on_activate=None, player=None):
        super().__init__()
        self.song = song
        self._on_activate = on_activate
        self._player = player
        self._player_handlers = []
        self.set_activatable(True)
        self.set_selectable(True)
        set_accessible_label(self, song.props.title)

        gesture = Gtk.GestureClick()
        gesture.set_button(0)
        gesture.connect("released", self._on_click_released)
        self.add_controller(gesture)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        box.add_css_class("song-item")
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(9)
        box.set_margin_end(9)

        if self._on_activate:
            self._play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
            self._play_button.add_css_class("flat")
            self._play_button.add_css_class("row-play")
            self._play_button.set_valign(Gtk.Align.CENTER)
            self._play_button.set_tooltip_text("Play")
            set_accessible_label(self._play_button, "Play")
            self._play_button.connect("clicked", self._on_play_clicked)
            box.append(self._play_button)
        else:
            self._play_button = None

        cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        cover.set_pixel_size(34)
        cover.add_css_class("album-cover")
        if song.props.thumbnail:
            cover.set_from_file(song.props.thumbnail)
        box.append(cover)

        track_label = Gtk.Label(
            label=str(song.props.track_number or ""),
            xalign=1,
            width_chars=3,
        )
        track_label.add_css_class("dim-label")
        box.append(track_label)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        title = Gtk.Label(label=song.props.title, xalign=0)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.add_css_class("song-title")
        text_box.append(title)

        if show_context:
            context = Gtk.Label(
                label=f"{song.props.artist} - {song.props.album}",
                xalign=0,
            )
            context.set_ellipsize(Pango.EllipsizeMode.END)
            context.add_css_class("caption")
            context.add_css_class("dim-label")
            text_box.append(context)

        box.append(text_box)

        duration = Gtk.Label(label=format_duration(song.props.duration))
        duration.set_width_chars(6)
        duration.add_css_class("dim-label")
        box.append(duration)

        self.set_child(box)

        if self._player:
            self._player_handlers = [
                self._player.connect("notify::current-song", self._sync_playing_state),
                self._player.connect("notify::play-state", self._sync_playing_state),
            ]
            self._sync_playing_state()

    def do_unroot(self):
        self._disconnect_player()
        Gtk.ListBoxRow.do_unroot(self)

    def _disconnect_player(self):
        if not self._player:
            return
        for handler_id in self._player_handlers:
            if self._player.handler_is_connected(handler_id):
                self._player.disconnect(handler_id)
        self._player_handlers.clear()

    def _on_click_released(self, _gesture, n_press, _x, _y):
        if n_press == 2 and self._on_activate:
            self._on_activate(self.song)

    def _on_play_clicked(self, _button):
        if self._player and self._player.props.current_song == self.song:
            self._player.play_pause()
        elif self._on_activate:
            self._on_activate(self.song)

    def _sync_playing_state(self, *_args):
        current_song = self._player.props.current_song
        is_current = current_song == self.song
        is_playing = self._player.props.play_state == int(PlayState.PLAYING)

        if is_current:
            self.add_css_class("playing")
        else:
            self.remove_css_class("playing")

        if self._play_button:
            label = "Pause" if is_current and is_playing else "Play"
            self._play_button.set_icon_name(
                "media-playback-pause-symbolic"
                if is_current and is_playing else "media-playback-start-symbolic"
            )
            self._play_button.set_tooltip_text(label)
            set_accessible_label(self._play_button, label)


class SongListItem(Gtk.Box):
    """Factory-backed song item whose signal lifetime follows its binding."""

    def __init__(self, player, on_activate, show_context: bool):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        self.add_css_class("song-item")
        self._player = player
        self._on_activate = on_activate
        self._show_context = show_context
        self._song = None
        self._player_handlers = []
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(9)
        self.set_margin_end(9)

        self._play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
        self._play_button.add_css_class("flat")
        self._play_button.add_css_class("row-play")
        self._play_button.set_valign(Gtk.Align.CENTER)
        self._play_button.connect("clicked", self._on_play_clicked)
        self.append(self._play_button)

        self._cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        self._cover.set_pixel_size(34)
        self._cover.add_css_class("album-cover")
        self.append(self._cover)

        self._track = Gtk.Label(xalign=1, width_chars=3)
        self._track.add_css_class("dim-label")
        self.append(self._track)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._title = Gtk.Label(xalign=0)
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        self._title.add_css_class("song-title")
        labels.append(self._title)
        self._context = Gtk.Label(xalign=0)
        self._context.set_ellipsize(Pango.EllipsizeMode.END)
        self._context.add_css_class("caption")
        self._context.add_css_class("dim-label")
        self._context.set_visible(show_context)
        labels.append(self._context)
        self.append(labels)

        self._duration = Gtk.Label(width_chars=6)
        self._duration.add_css_class("dim-label")
        self.append(self._duration)

    @property
    def song(self):
        return self._song

    def bind(self, song):
        self.unbind()
        self._song = song
        self._title.set_label(song.props.title)
        self._context.set_label(f"{song.props.artist} — {song.props.album}")
        self._track.set_label(str(song.props.track_number or ""))
        self._duration.set_label(format_duration(song.props.duration))
        if song.props.thumbnail:
            self._cover.set_from_file(song.props.thumbnail)
        else:
            self._cover.set_from_icon_name("audio-x-generic-symbolic")
        set_accessible_label(self, song.props.title)
        self._player_handlers = [
            self._player.connect("notify::current-song", self._sync_playing_state),
            self._player.connect("notify::play-state", self._sync_playing_state),
        ]
        self._sync_playing_state()

    def unbind(self):
        for handler_id in self._player_handlers:
            if self._player.handler_is_connected(handler_id):
                self._player.disconnect(handler_id)
        self._player_handlers.clear()
        self._song = None
        self.remove_css_class("playing")

    def _on_play_clicked(self, _button):
        if self._song is None:
            return
        if self._player.props.current_song == self._song:
            self._player.play_pause()
        else:
            self._on_activate(self._song)

    def _sync_playing_state(self, *_args):
        if self._song is None:
            return
        is_current = self._player.props.current_song == self._song
        is_playing = self._player.props.play_state == int(PlayState.PLAYING)
        if is_current:
            self.add_css_class("playing")
        else:
            self.remove_css_class("playing")
        label = "Pause" if is_current and is_playing else "Play"
        self._play_button.set_icon_name(
            "media-playback-pause-symbolic"
            if is_current and is_playing else "media-playback-start-symbolic"
        )
        self._play_button.set_tooltip_text(label)
        set_accessible_label(self._play_button, label)


def create_song_factory(player, on_activate, show_context: bool = True):
    factory = Gtk.SignalListItemFactory()

    def setup(_factory, list_item):
        list_item.set_child(SongListItem(player, on_activate, show_context))

    def bind(_factory, list_item):
        list_item.get_child().bind(list_item.get_item())

    def unbind(_factory, list_item):
        list_item.get_child().unbind()

    factory.connect("setup", setup)
    factory.connect("bind", bind)
    factory.connect("unbind", unbind)
    return factory
