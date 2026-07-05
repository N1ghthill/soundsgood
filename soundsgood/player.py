# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import random

import gi

gi.require_version("Gst", "1.0")

from gi.repository import GLib, GObject, Gst

from soundsgood.models import PlayState, RepeatMode, Song


class Player(GObject.GObject):
    """GStreamer-backed music player."""

    __gsignals__ = {
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "playlist-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    current_song = GObject.Property(type=object, default=None)
    play_state = GObject.Property(type=int, default=int(PlayState.STOPPED))
    repeat_mode = GObject.Property(type=int, default=int(RepeatMode.NONE))
    volume = GObject.Property(type=float, default=1.0)
    mute = GObject.Property(type=bool, default=False)
    position = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=0)

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._settings = application.props.settings
        self._playlist: list[Song] = []
        self._playlist_index = -1

        self._playbin = Gst.ElementFactory.make("playbin", "soundsgood-player")
        if self._playbin is None:
            raise RuntimeError("GStreamer playbin is not available")

        self._bus = self._playbin.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_bus_message)

        self.props.volume = self._settings.get_double("volume")
        self.props.mute = self._settings.get_boolean("mute")
        self.props.repeat_mode = self._settings.get_enum("repeat")

        self.connect("notify::volume", self._on_volume_changed)
        self.connect("notify::mute", self._on_mute_changed)
        self.connect("notify::repeat-mode", self._on_repeat_mode_changed)
        self._apply_audio_properties()

        GLib.timeout_add(500, self._tick)

    def play_song(self, song: Song, playlist: list[Song] | None = None):
        """Play a song, optionally replacing the playback queue."""
        if playlist is not None:
            self._playlist = list(playlist)
            self.emit("playlist-changed")
        elif song not in self._playlist:
            self._playlist = [song]
            self.emit("playlist-changed")

        try:
            self._playlist_index = self._playlist.index(song)
        except ValueError:
            self._playlist.append(song)
            self._playlist_index = len(self._playlist) - 1
            self.emit("playlist-changed")

        self.props.play_state = int(PlayState.LOADING)
        self.props.position = 0
        self.props.duration = song.props.duration

        if not self._load_song(song):
            return

        self.props.current_song = song
        self.props.play_state = int(PlayState.PLAYING)

    def play_pause(self):
        if self.props.current_song is None:
            if self._playlist:
                self.play_song(self._playlist[0], self._playlist)
            return

        if self.props.play_state == int(PlayState.PLAYING):
            self.pause()
        else:
            if self._set_state(Gst.State.PLAYING):
                self.props.play_state = int(PlayState.PLAYING)

    def pause(self):
        if self._set_state(Gst.State.PAUSED):
            self.props.play_state = int(PlayState.PAUSED)

    def stop(self, clear_current: bool = False):
        self._set_state(Gst.State.NULL)
        self.props.play_state = int(PlayState.STOPPED)
        self.props.position = 0
        if clear_current:
            self.props.current_song = None

    def next(self):
        if not self._playlist:
            return

        next_song = self._get_next_song(user_initiated=True)
        if next_song:
            self.play_song(next_song, self._playlist)
        else:
            self.stop()

    def previous(self):
        if not self._playlist:
            return

        if self.props.position > 3:
            self.seek(0)
            return

        self._playlist_index = max(0, self._playlist_index - 1)
        self.play_song(self._playlist[self._playlist_index], self._playlist)

    def play_playlist_index(self, index: int):
        if index < 0 or index >= len(self._playlist):
            return

        self.play_song(self._playlist[index], self._playlist)

    def clear_playlist(self):
        self._playlist = []
        self._playlist_index = -1
        self.stop(clear_current=True)
        self.emit("playlist-changed")

    def remove_playlist_index(self, index: int):
        if index < 0 or index >= len(self._playlist):
            return

        removing_current = index == self._playlist_index
        del self._playlist[index]

        if not self._playlist:
            self._playlist_index = -1
            self.stop(clear_current=True)
            self.emit("playlist-changed")
            return

        if index < self._playlist_index:
            self._playlist_index -= 1
        elif removing_current:
            self._playlist_index = min(index, len(self._playlist) - 1)
            self.play_song(self._playlist[self._playlist_index], self._playlist)
            return

        self.emit("playlist-changed")

    def get_playlist(self) -> list[Song]:
        return list(self._playlist)

    def get_playlist_index(self) -> int:
        return self._playlist_index

    def seek(self, position: int):
        position = max(0, position)
        if self.props.current_song is None:
            return

        success = self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            position * Gst.SECOND,
        )
        if success:
            self.props.position = position

    def _load_song(self, song: Song) -> bool:
        if not song.props.url:
            self.emit("error", "Song has no playable URI")
            self.stop(clear_current=True)
            return False

        self._set_state(Gst.State.NULL)
        self._playbin.get_state(Gst.SECOND)
        self._playbin.set_property("uri", song.props.url)
        self._apply_audio_properties()

        return self._set_state(Gst.State.PLAYING)

    def _set_state(self, state: Gst.State) -> bool:
        result = self._playbin.set_state(state)
        if result == Gst.StateChangeReturn.FAILURE:
            self.emit("error", f"Could not change playback state to {state.value_nick}")
            return False

        return True

    def _get_next_song(self, user_initiated: bool = False) -> Song | None:
        repeat_mode = self.props.repeat_mode

        if repeat_mode == int(RepeatMode.SONG) and not user_initiated:
            return self.props.current_song

        if repeat_mode == int(RepeatMode.SHUFFLE):
            if len(self._playlist) == 1:
                return self._playlist[0]
            choices = [
                song for i, song in enumerate(self._playlist)
                if i != self._playlist_index
            ]
            song = random.choice(choices)
            self._playlist_index = self._playlist.index(song)
            return song

        next_index = self._playlist_index + 1
        if next_index < len(self._playlist):
            self._playlist_index = next_index
            return self._playlist[self._playlist_index]

        if repeat_mode == int(RepeatMode.ALL):
            self._playlist_index = 0
            return self._playlist[0]

        return None

    def _on_bus_message(self, _bus, message):
        if message.type == Gst.MessageType.EOS:
            next_song = self._get_next_song()
            if next_song:
                self.play_song(next_song, self._playlist)
            else:
                self.stop()
        elif message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            self.emit("error", error.message)
            if debug:
                print(debug)
            self.stop(clear_current=True)
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            self._update_duration()

    def _tick(self):
        if self.props.play_state == int(PlayState.PLAYING):
            self._update_position()
            self._update_duration()
        return GLib.SOURCE_CONTINUE

    def _update_position(self):
        success, position = self._playbin.query_position(Gst.Format.TIME)
        if success:
            self.props.position = int(position / Gst.SECOND)

    def _update_duration(self):
        success, duration = self._playbin.query_duration(Gst.Format.TIME)
        if success and duration > 0:
            self.props.duration = int(duration / Gst.SECOND)

    def _apply_audio_properties(self):
        self._playbin.set_property("volume", self.props.volume)
        self._playbin.set_property("mute", self.props.mute)

    def _on_volume_changed(self, *_args):
        self._playbin.set_property("volume", self.props.volume)
        self._settings.set_double("volume", self.props.volume)

    def _on_mute_changed(self, *_args):
        self._playbin.set_property("mute", self.props.mute)
        self._settings.set_boolean("mute", self.props.mute)

    def _on_repeat_mode_changed(self, *_args):
        self._settings.set_enum("repeat", self.props.repeat_mode)
