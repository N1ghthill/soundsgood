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
        self.set_activatable(True)
        self.set_selectable(True)
        set_accessible_label(self, song.props.title)

        gesture = Gtk.GestureClick()
        gesture.set_button(0)
        gesture.connect("released", self._on_click_released)
        self.add_controller(gesture)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        if self._on_activate:
            self._play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
            self._play_button.add_css_class("flat")
            self._play_button.set_tooltip_text("Play")
            set_accessible_label(self._play_button, "Play")
            self._play_button.connect("clicked", self._on_play_clicked)
            box.append(self._play_button)
        else:
            self._play_button = None

        cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        cover.set_pixel_size(40)
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
            self._player.connect("notify::current-song", self._sync_playing_state)
            self._player.connect("notify::play-state", self._sync_playing_state)
            self._sync_playing_state()

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
