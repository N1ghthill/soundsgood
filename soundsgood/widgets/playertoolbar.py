# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk, Pango

from soundsgood.models import PlayState, RepeatMode, Song
from soundsgood.widgets.songrow import format_duration, set_accessible_label


class QueueListItem(Gtk.Box):
    """Factory-backed queue row; only visible items have widgets."""

    def __init__(self, on_remove):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._index = -1
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._number = Gtk.Label(width_chars=3, xalign=1)
        self._number.add_css_class("dim-label")
        self.append(self._number)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._title = Gtk.Label(xalign=0)
        self._title.add_css_class("song-title")
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(self._title)
        self._context = Gtk.Label(xalign=0)
        self._context.add_css_class("caption")
        self._context.add_css_class("dim-label")
        self._context.set_ellipsize(Pango.EllipsizeMode.END)
        labels.append(self._context)
        self.append(labels)

        self._duration = Gtk.Label(width_chars=6)
        self._duration.add_css_class("dim-label")
        self.append(self._duration)

        remove_button = Gtk.Button(icon_name="list-remove-symbolic")
        remove_button.add_css_class("flat")
        remove_button.set_tooltip_text(_("Remove from queue"))
        set_accessible_label(remove_button, _("Remove from queue"))
        remove_button.connect("clicked", lambda *_: on_remove(self._index))
        self.append(remove_button)

    def bind(self, index, song):
        self._index = index
        self._number.set_label(str(index + 1))
        self._title.set_label(song.props.title)
        self._context.set_label(f"{song.props.artist} — {song.props.album}")
        self._duration.set_label(format_duration(song.props.duration))
        set_accessible_label(self, song.props.title)


class PlayerToolbar(Gtk.Box):
    """Bottom playback controls."""

    def __init__(self, application):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._app = application
        self._player = application.props.player
        self._updating = False

        self.add_css_class("player-toolbar")
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_visible(False)

        controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_row.set_hexpand(True)
        self.append(controls_row)

        self._previous_button = Gtk.Button(icon_name="media-skip-backward-symbolic")
        self._previous_button.set_tooltip_text(_("Previous"))
        set_accessible_label(self._previous_button, _("Previous"))
        self._previous_button.connect("clicked", lambda *_: self._player.previous())
        controls_row.append(self._previous_button)

        self._play_button = Gtk.Button(icon_name="media-playback-start-symbolic")
        self._play_button.add_css_class("suggested-action")
        self._play_button.set_tooltip_text(_("Play/Pause"))
        set_accessible_label(self._play_button, _("Play/Pause"))
        self._play_button.connect("clicked", lambda *_: self._player.play_pause())
        controls_row.append(self._play_button)

        self._next_button = Gtk.Button(icon_name="media-skip-forward-symbolic")
        self._next_button.set_tooltip_text(_("Next"))
        set_accessible_label(self._next_button, _("Next"))
        self._next_button.connect("clicked", lambda *_: self._player.next())
        controls_row.append(self._next_button)

        self._cover = Gtk.Image(icon_name="audio-x-generic-symbolic")
        self._cover.set_pixel_size(48)
        controls_row.append(self._cover)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        self._title_label = Gtk.Label(label=_("Not playing"), xalign=0)
        self._title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label = Gtk.Label(xalign=0)
        self._artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._artist_label.add_css_class("caption")
        self._artist_label.add_css_class("dim-label")
        info_box.append(self._title_label)
        info_box.append(self._artist_label)
        controls_row.append(info_box)

        self._position_label = Gtk.Label(label="0:00")
        self._position_label.set_width_chars(6)
        self._position_label.add_css_class("caption")
        self._position_label.add_css_class("dim-label")

        progress_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        progress_row.set_hexpand(True)
        self.append(progress_row)
        progress_row.append(self._position_label)

        self._progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self._progress.set_draw_value(False)
        self._progress.set_hexpand(True)
        self._progress.set_tooltip_text(_("Seek"))
        set_accessible_label(self._progress, _("Seek"))
        self._progress.connect("change-value", self._on_seek)
        progress_row.append(self._progress)

        self._duration_label = Gtk.Label(label="--:--")
        self._duration_label.set_width_chars(6)
        self._duration_label.add_css_class("caption")
        self._duration_label.add_css_class("dim-label")
        progress_row.append(self._duration_label)

        self._repeat_button = Gtk.Button(icon_name="media-playlist-consecutive-symbolic")
        self._repeat_button.set_tooltip_text(_("Repeat mode"))
        set_accessible_label(self._repeat_button, _("Repeat mode"))
        self._repeat_button.connect("clicked", self._on_repeat_clicked)

        self._queue_popover = Gtk.Popover()
        queue_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        queue_box.set_size_request(280, 300)
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
        set_accessible_label(clear_button, _("Clear queue"))
        clear_button.connect("clicked", self._on_clear_queue)
        queue_header.append(clear_button)
        queue_box.append(queue_header)

        self._queue_model = Gio.ListStore(item_type=Song)
        self._queue_selection = Gtk.SingleSelection(model=self._queue_model)
        self._queue_selection.set_autoselect(False)
        self._queue_selection.set_can_unselect(True)
        queue_factory = Gtk.SignalListItemFactory()
        queue_factory.connect("setup", self._setup_queue_item)
        queue_factory.connect("bind", self._bind_queue_item)
        self._queue_list = Gtk.ListView(
            model=self._queue_selection,
            factory=queue_factory,
        )
        self._queue_list.set_single_click_activate(False)
        self._queue_list.connect("activate", self._on_queue_item_activated)

        queue_scroller = Gtk.ScrolledWindow()
        queue_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        queue_scroller.set_vexpand(True)
        queue_scroller.set_child(self._queue_list)
        self._queue_stack = Gtk.Stack()
        self._queue_stack.set_vexpand(True)
        self._queue_stack.add_named(queue_scroller, "queue")
        empty_label = Gtk.Label(label=_("Queue is empty"))
        empty_label.add_css_class("dim-label")
        self._queue_stack.add_named(empty_label, "empty")
        queue_box.append(self._queue_stack)
        self._queue_popover.set_child(queue_box)

        self._queue_button = Gtk.MenuButton(icon_name="view-list-symbolic")
        self._queue_button.set_tooltip_text(_("Queue"))
        set_accessible_label(self._queue_button, _("Queue"))
        self._queue_button.set_popover(self._queue_popover)
        controls_row.append(self._queue_button)

        self._volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.01)
        self._volume.set_draw_value(False)
        self._volume.set_size_request(96, -1)
        self._volume.set_tooltip_text(_("Volume"))
        set_accessible_label(self._volume, _("Volume"))
        self._volume.set_value(self._player.props.volume)
        self._volume.connect("value-changed", self._on_volume_changed)

        secondary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        secondary_box.set_margin_top(12)
        secondary_box.set_margin_bottom(12)
        secondary_box.set_margin_start(12)
        secondary_box.set_margin_end(12)

        repeat_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        repeat_label = Gtk.Label(label=_("Repeat and shuffle"), xalign=0)
        repeat_label.set_hexpand(True)
        repeat_row.append(repeat_label)
        repeat_row.append(self._repeat_button)
        secondary_box.append(repeat_row)

        volume_label = Gtk.Label(label=_("Volume"), xalign=0)
        volume_label.add_css_class("caption")
        volume_label.add_css_class("dim-label")
        secondary_box.append(volume_label)
        self._volume.set_hexpand(True)
        secondary_box.append(self._volume)

        self._secondary_popover = Gtk.Popover()
        self._secondary_popover.set_child(secondary_box)
        self._secondary_button = Gtk.MenuButton(icon_name="emblem-system-symbolic")
        self._secondary_button.set_tooltip_text(_("Playback options"))
        set_accessible_label(self._secondary_button, _("Playback options"))
        self._secondary_button.set_popover(self._secondary_popover)
        controls_row.append(self._secondary_button)

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
        playlist = self._player.get_playlist()
        self._queue_model.remove_all()
        if not playlist:
            self._queue_stack.set_visible_child_name("empty")
            self._queue_button.set_sensitive(False)
            return

        self._queue_button.set_sensitive(True)
        self._queue_stack.set_visible_child_name("queue")
        for song in playlist:
            self._queue_model.append(song)

        self._sync_queue_rows()

    def _setup_queue_item(self, _factory, list_item):
        list_item.set_child(QueueListItem(self._on_remove_queue_item))

    def _bind_queue_item(self, _factory, list_item):
        list_item.get_child().bind(list_item.get_position(), list_item.get_item())

    def _sync_queue_rows(self):
        current_index = self._player.get_playlist_index()
        if 0 <= current_index < self._queue_model.get_n_items():
            self._queue_selection.select_item(current_index, True)
        else:
            self._queue_selection.unselect_all()

    def _on_queue_item_activated(self, _list_view, position):
        if 0 <= position < self._queue_model.get_n_items():
            self._player.play_playlist_index(position)
            self._queue_popover.popdown()

    def _on_clear_queue(self, _button):
        self._player.clear_playlist()
        self._queue_popover.popdown()

    def _on_remove_queue_item(self, index):
        if 0 <= index < self._queue_model.get_n_items():
            self._player.remove_playlist_index(index)
