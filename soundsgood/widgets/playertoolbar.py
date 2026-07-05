# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from soundsgood.models import PlayState, RepeatMode
from soundsgood.widgets.songrow import format_duration


class PlayerToolbar(Gtk.Box):
    """Bottom playback controls."""

    def __init__(self, application):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._app = application
        self._player = application.props.player
        self._updating = False

        self.add_css_class("player-toolbar")
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_visible(False)

        self._previous_button = Gtk.Button(icon_name="media-skip-backward-symbolic")
        self._previous_button.set_tooltip_text(_("Previous"))
        self._previous_button.connect("clicked", lambda *_: self._player.previous())
        self.append(self._previous_button)

        self._play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
        self._play_button.add_css_class("suggested-action")
        self._play_button.set_tooltip_text(_("Play/Pause"))
        self._play_button.connect("clicked", lambda *_: self._player.play_pause())
        self.append(self._play_button)

        self._next_button = Gtk.Button(icon_name="media-skip-forward-symbolic")
        self._next_button.set_tooltip_text(_("Next"))
        self._next_button.connect("clicked", lambda *_: self._player.next())
        self.append(self._next_button)

        self._cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        self._cover.set_pixel_size(48)
        self.append(self._cover)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_size_request(220, -1)
        self._title_label = Gtk.Label(label=_("Not playing"), xalign=0)
        self._title_label.set_ellipsize(3)
        self._artist_label = Gtk.Label(xalign=0)
        self._artist_label.set_ellipsize(3)
        self._artist_label.add_css_class("caption")
        self._artist_label.add_css_class("dim-label")
        info_box.append(self._title_label)
        info_box.append(self._artist_label)
        self.append(info_box)

        self._position_label = Gtk.Label(label="0:00")
        self._position_label.add_css_class("caption")
        self._position_label.add_css_class("dim-label")
        self.append(self._position_label)

        self._progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self._progress.set_draw_value(False)
        self._progress.set_hexpand(True)
        self._progress.connect("change-value", self._on_seek)
        self.append(self._progress)

        self._duration_label = Gtk.Label(label="--:--")
        self._duration_label.add_css_class("caption")
        self._duration_label.add_css_class("dim-label")
        self.append(self._duration_label)

        self._repeat_button = Gtk.Button(icon_name="media-playlist-consecutive-symbolic")
        self._repeat_button.set_tooltip_text(_("Repeat mode"))
        self._repeat_button.connect("clicked", self._on_repeat_clicked)
        self.append(self._repeat_button)

        self._queue_popover = Gtk.Popover()
        self._queue_popover.set_size_request(420, 360)
        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_margin_top(12)
        queue_box.set_margin_bottom(12)
        queue_box.set_margin_start(12)
        queue_box.set_margin_end(12)

        queue_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        queue_title = Gtk.Label(label=_("Queue"), xalign=0)
        queue_title.add_css_class("heading")
        queue_title.set_hexpand(True)
        queue_header.append(queue_title)
        clear_button = Gtk.Button(icon_name="edit-clear-symbolic")
        clear_button.set_tooltip_text(_("Clear queue"))
        clear_button.connect("clicked", self._on_clear_queue)
        queue_header.append(clear_button)
        queue_box.append(queue_header)

        self._queue_list = Gtk.ListBox()
        self._queue_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._queue_list.set_activate_on_single_click(False)
        self._queue_list.connect("row-activated", self._on_queue_row_activated)

        queue_scroller = Gtk.ScrolledWindow()
        queue_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        queue_scroller.set_vexpand(True)
        queue_scroller.set_child(self._queue_list)
        queue_box.append(queue_scroller)
        self._queue_popover.set_child(queue_box)

        self._queue_button = Gtk.MenuButton(icon_name="view-list-symbolic")
        self._queue_button.set_tooltip_text(_("Queue"))
        self._queue_button.set_popover(self._queue_popover)
        self.append(self._queue_button)

        self._volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self._volume.set_draw_value(False)
        self._volume.set_size_request(110, -1)
        self._volume.set_value(self._player.props.volume)
        self._volume.connect("value-changed", self._on_volume_changed)
        self.append(self._volume)

        for prop in (
            "current-song",
            "play-state",
            "position",
            "duration",
            "repeat-mode",
            "volume",
        ):
            self._player.connect(f"notify::{prop}", self._sync)
        self._player.connect("playlist-changed", self._sync_queue)

        self._sync()
        self._sync_queue()

    def _sync(self, *_args):
        song = self._player.props.current_song
        self.set_visible(song is not None)
        if song:
            self._title_label.set_label(song.props.title)
            self._artist_label.set_label(song.props.artist)
            if song.props.thumbnail:
                self._cover.set_from_file(song.props.thumbnail)
            else:
                self._cover.set_from_icon_name("audio-x-generic-symbolic")

        is_playing = self._player.props.play_state == int(PlayState.PLAYING)
        self._play_button.set_icon_name(
            "media-playback-pause-symbolic"
            if is_playing else "media-playback-start-symbolic"
        )

        duration = max(1, self._player.props.duration)
        position = min(self._player.props.position, duration)
        self._position_label.set_label(format_duration(position))
        self._duration_label.set_label(format_duration(self._player.props.duration))

        self._updating = True
        self._progress.set_range(0, duration)
        self._progress.set_value(position)
        self._volume.set_value(self._player.props.volume)
        self._updating = False

        icon = {
            int(RepeatMode.NONE): "media-playlist-consecutive-symbolic",
            int(RepeatMode.ALL): "media-playlist-repeat-symbolic",
            int(RepeatMode.SONG): "media-playlist-repeat-song-symbolic",
            int(RepeatMode.SHUFFLE): "media-playlist-shuffle-symbolic",
        }.get(self._player.props.repeat_mode, "media-playlist-consecutive-symbolic")
        self._repeat_button.set_icon_name(icon)
        self._sync_queue_rows()

    def _on_seek(self, _scale, _scroll, value):
        if not self._updating:
            self._player.seek(int(value))
        return False

    def _on_volume_changed(self, scale):
        if not self._updating:
            self._player.props.volume = scale.get_value()

    def _on_repeat_clicked(self, _button):
        modes = [RepeatMode.NONE, RepeatMode.ALL, RepeatMode.SONG, RepeatMode.SHUFFLE]
        current = RepeatMode(self._player.props.repeat_mode)
        self._player.props.repeat_mode = int(modes[(modes.index(current) + 1) % len(modes)])

    def _sync_queue(self, *_args):
        self._clear_queue_list()
        playlist = self._player.get_playlist()
        if not playlist:
            placeholder = Gtk.ListBoxRow()
            placeholder.set_selectable(False)
            placeholder.set_activatable(False)
            label = Gtk.Label(label=_("Queue is empty"))
            label.add_css_class("dim-label")
            label.set_margin_top(24)
            label.set_margin_bottom(24)
            placeholder.set_child(label)
            self._queue_list.append(placeholder)
            self._queue_button.set_sensitive(False)
            return

        self._queue_button.set_sensitive(True)
        for index, song in enumerate(playlist):
            self._queue_list.append(self._queue_row(index, song))

        self._sync_queue_rows()

    def _queue_row(self, index, song):
        row = Gtk.ListBoxRow()
        row.queue_index = index
        row.song = song

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        number = Gtk.Label(label=str(index + 1), width_chars=3, xalign=1)
        number.add_css_class("dim-label")
        box.append(number)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        title = Gtk.Label(label=song.props.title, xalign=0)
        title.add_css_class("song-title")
        labels.append(title)
        context = Gtk.Label(label=f"{song.props.artist} - {song.props.album}", xalign=0)
        context.add_css_class("caption")
        context.add_css_class("dim-label")
        labels.append(context)
        box.append(labels)

        duration = Gtk.Label(label=format_duration(song.props.duration))
        duration.add_css_class("dim-label")
        box.append(duration)

        remove_button = Gtk.Button(icon_name="list-remove-symbolic")
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text(_("Remove from queue"))
        remove_button.queue_index = index
        remove_button.connect("clicked", self._on_remove_queue_item)
        box.append(remove_button)

        row.set_child(box)
        return row

    def _sync_queue_rows(self):
        current_index = self._player.get_playlist_index()
        row = self._queue_list.get_first_child()
        while row:
            if hasattr(row, "queue_index") and row.queue_index == current_index:
                row.add_css_class("playing")
                self._queue_list.select_row(row)
            else:
                row.remove_css_class("playing")
            row = row.get_next_sibling()

    def _clear_queue_list(self):
        child = self._queue_list.get_first_child()
        while child:
            self._queue_list.remove(child)
            child = self._queue_list.get_first_child()

    def _on_queue_row_activated(self, _listbox, row):
        if hasattr(row, "queue_index"):
            self._player.play_playlist_index(row.queue_index)
            self._queue_popover.popdown()

    def _on_clear_queue(self, _button):
        self._player.clear_playlist()
        self._queue_popover.popdown()

    def _on_remove_queue_item(self, button):
        self._player.remove_playlist_index(button.queue_index)
