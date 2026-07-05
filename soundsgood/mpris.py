# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import hashlib

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib

from soundsgood.models import PlayState, RepeatMode


MPRIS_OBJECT_PATH = "/org/mpris/MediaPlayer2"
MPRIS_BUS_NAME = "org.mpris.MediaPlayer2.SoundsGood"


ROOT_XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="Fullscreen" type="b" access="readwrite"/>
    <property name="CanSetFullscreen" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
</node>
"""


PLAYER_XML = """
<node>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek">
      <arg direction="in" name="Offset" type="x"/>
    </method>
    <method name="SetPosition">
      <arg direction="in" name="TrackId" type="o"/>
      <arg direction="in" name="Position" type="x"/>
    </method>
    <method name="OpenUri">
      <arg direction="in" name="Uri" type="s"/>
    </method>
    <signal name="Seeked">
      <arg name="Position" type="x"/>
    </signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""


class MprisService:
    """Expose the player through the MPRIS D-Bus interface."""

    def __init__(self, application):
        self._app = application
        self._player = application.props.player
        self._connection = None
        self._registration_ids = []
        self._owner_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            MPRIS_BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            None,
            self._on_name_lost,
        )

        for prop in (
            "current-song",
            "play-state",
            "repeat-mode",
            "volume",
            "position",
            "duration",
        ):
            self._player.connect(f"notify::{prop}", self._on_player_changed)
        self._player.connect("playlist-changed", self._on_playlist_changed)

    def shutdown(self):
        if self._connection:
            for registration_id in self._registration_ids:
                self._connection.unregister_object(registration_id)
        self._registration_ids.clear()

        if self._owner_id:
            Gio.bus_unown_name(self._owner_id)
            self._owner_id = 0

    def _on_bus_acquired(self, connection, _name):
        self._connection = connection
        root_node = Gio.DBusNodeInfo.new_for_xml(ROOT_XML)
        player_node = Gio.DBusNodeInfo.new_for_xml(PLAYER_XML)

        self._registration_ids.append(
            connection.register_object(
                MPRIS_OBJECT_PATH,
                root_node.interfaces[0],
                self._on_method_call,
                self._get_property,
                self._set_property,
            )
        )
        self._registration_ids.append(
            connection.register_object(
                MPRIS_OBJECT_PATH,
                player_node.interfaces[0],
                self._on_method_call,
                self._get_property,
                self._set_property,
            )
        )

    def _on_name_lost(self, _connection, _name):
        self._connection = None
        self._registration_ids.clear()

    def _on_method_call(
        self,
        _connection,
        _sender,
        _object_path,
        interface_name,
        method_name,
        parameters,
        invocation,
    ):
        if interface_name == "org.mpris.MediaPlayer2":
            self._handle_root_method(method_name)
            invocation.return_value(None)
            return

        if interface_name != "org.mpris.MediaPlayer2.Player":
            invocation.return_dbus_error(
                "org.mpris.MediaPlayer2.Error.NotSupported",
                f"Unsupported interface {interface_name}",
            )
            return

        try:
            self._handle_player_method(method_name, parameters)
        except ValueError as error:
            invocation.return_dbus_error(
                "org.mpris.MediaPlayer2.Error.InvalidArgs",
                str(error),
            )
            return

        invocation.return_value(None)

    def _handle_root_method(self, method_name: str):
        if method_name == "Raise":
            window = self._app.props.window
            if window:
                window.present()
        elif method_name == "Quit":
            self._app.quit()

    def _handle_player_method(self, method_name: str, parameters):
        if method_name == "Next":
            self._player.next()
        elif method_name == "Previous":
            self._player.previous()
        elif method_name == "Pause":
            self._player.pause()
        elif method_name == "PlayPause":
            self._player.play_pause()
        elif method_name == "Stop":
            self._player.stop(clear_current=False)
        elif method_name == "Play":
            if self._player.props.play_state != int(PlayState.PLAYING):
                self._player.play_pause()
        elif method_name == "Seek":
            offset_us = parameters.unpack()[0]
            target = max(0, self._player.props.position + int(offset_us / 1_000_000))
            self._player.seek(target)
            self._emit_seeked()
        elif method_name == "SetPosition":
            track_id, position_us = parameters.unpack()
            if track_id != self._track_id():
                return
            self._player.seek(max(0, int(position_us / 1_000_000)))
            self._emit_seeked()
        elif method_name == "OpenUri":
            raise ValueError("OpenUri is not supported")

    def _get_property(
        self,
        _connection,
        _sender,
        _object_path,
        interface_name,
        property_name,
    ):
        if interface_name == "org.mpris.MediaPlayer2":
            return self._root_property(property_name)
        if interface_name == "org.mpris.MediaPlayer2.Player":
            return self._player_property(property_name)
        return None

    def _set_property(
        self,
        _connection,
        _sender,
        _object_path,
        interface_name,
        property_name,
        value,
    ):
        if interface_name != "org.mpris.MediaPlayer2.Player":
            return False

        if property_name == "Volume":
            self._player.props.volume = min(1.0, max(0.0, value.unpack()))
            return True
        if property_name == "LoopStatus":
            self._player.props.repeat_mode = int(self._repeat_from_loop_status(value.unpack()))
            return True
        if property_name == "Shuffle":
            if value.unpack():
                self._player.props.repeat_mode = int(RepeatMode.SHUFFLE)
            elif self._player.props.repeat_mode == int(RepeatMode.SHUFFLE):
                self._player.props.repeat_mode = int(RepeatMode.NONE)
            return True
        if property_name == "Rate":
            return value.unpack() == 1.0

        return False

    def _root_property(self, property_name: str):
        values = {
            "CanQuit": GLib.Variant("b", True),
            "Fullscreen": GLib.Variant("b", False),
            "CanSetFullscreen": GLib.Variant("b", False),
            "CanRaise": GLib.Variant("b", True),
            "HasTrackList": GLib.Variant("b", False),
            "Identity": GLib.Variant("s", "SoundsGood"),
            "DesktopEntry": GLib.Variant("s", "io.github.irving.soundsgood"),
            "SupportedUriSchemes": GLib.Variant("as", ["file"]),
            "SupportedMimeTypes": GLib.Variant(
                "as",
                [
                    "audio/mpeg",
                    "audio/flac",
                    "audio/ogg",
                    "audio/wav",
                    "audio/mp4",
                ],
            ),
        }
        return values.get(property_name)

    def _player_property(self, property_name: str):
        values = {
            "PlaybackStatus": GLib.Variant("s", self._playback_status()),
            "LoopStatus": GLib.Variant("s", self._loop_status()),
            "Rate": GLib.Variant("d", 1.0),
            "Shuffle": GLib.Variant("b", self._player.props.repeat_mode == int(RepeatMode.SHUFFLE)),
            "Metadata": GLib.Variant("a{sv}", self._metadata()),
            "Volume": GLib.Variant("d", self._player.props.volume),
            "Position": GLib.Variant("x", self._player.props.position * 1_000_000),
            "MinimumRate": GLib.Variant("d", 1.0),
            "MaximumRate": GLib.Variant("d", 1.0),
            "CanGoNext": GLib.Variant("b", self._can_go_next()),
            "CanGoPrevious": GLib.Variant("b", self._can_go_previous()),
            "CanPlay": GLib.Variant("b", self._can_play()),
            "CanPause": GLib.Variant("b", self._can_pause()),
            "CanSeek": GLib.Variant("b", self._can_seek()),
            "CanControl": GLib.Variant("b", True),
        }
        return values.get(property_name)

    def _playback_status(self) -> str:
        state = self._player.props.play_state
        if state == int(PlayState.PLAYING):
            return "Playing"
        if state == int(PlayState.PAUSED):
            return "Paused"
        return "Stopped"

    def _loop_status(self) -> str:
        repeat_mode = self._player.props.repeat_mode
        if repeat_mode == int(RepeatMode.SONG):
            return "Track"
        if repeat_mode == int(RepeatMode.ALL):
            return "Playlist"
        return "None"

    def _repeat_from_loop_status(self, loop_status: str) -> RepeatMode:
        if loop_status == "Track":
            return RepeatMode.SONG
        if loop_status == "Playlist":
            return RepeatMode.ALL
        return RepeatMode.NONE

    def _playlist(self) -> list:
        if hasattr(self._player, "get_playlist"):
            return self._player.get_playlist()
        return []

    def _playlist_index(self) -> int:
        if hasattr(self._player, "get_playlist_index"):
            return self._player.get_playlist_index()
        return -1

    def _can_go_next(self) -> bool:
        playlist = self._playlist()
        if not playlist:
            return False

        repeat_mode = self._player.props.repeat_mode
        if repeat_mode in (int(RepeatMode.ALL), int(RepeatMode.SHUFFLE)):
            return True

        return self._playlist_index() + 1 < len(playlist)

    def _can_go_previous(self) -> bool:
        return bool(self._playlist()) and self._player.props.current_song is not None

    def _can_play(self) -> bool:
        return self._player.props.current_song is not None or bool(self._playlist())

    def _can_pause(self) -> bool:
        return self._player.props.current_song is not None

    def _can_seek(self) -> bool:
        song = self._player.props.current_song
        return song is not None and max(self._player.props.duration, song.props.duration) > 0

    def _metadata(self) -> dict:
        song = self._player.props.current_song
        metadata = {
            "mpris:trackid": GLib.Variant("o", self._track_id()),
        }
        if song is None:
            return metadata

        metadata.update(
            {
                "xesam:title": GLib.Variant("s", song.props.title),
                "xesam:artist": GLib.Variant("as", [song.props.artist]),
                "xesam:album": GLib.Variant("s", song.props.album),
                "xesam:albumArtist": GLib.Variant("as", [song.props.album_artist]),
                "mpris:length": GLib.Variant("x", song.props.duration * 1_000_000),
                "xesam:url": GLib.Variant("s", song.props.url),
            }
        )
        if song.props.thumbnail:
            metadata["mpris:artUrl"] = GLib.Variant(
                "s",
                Gio.File.new_for_path(song.props.thumbnail).get_uri(),
            )

        return metadata

    def _track_id(self) -> str:
        song = self._player.props.current_song
        if song is None or not song.props.url:
            return "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        safe_id = hashlib.sha256(song.props.url.encode("utf-8")).hexdigest()
        return f"/org/mpris/MediaPlayer2/TrackList/{safe_id}"

    def _on_player_changed(self, _player, pspec):
        if not self._connection:
            return

        property_map = {
            "current-song": [
                "Metadata",
                "CanGoNext",
                "CanGoPrevious",
                "CanPlay",
                "CanPause",
                "CanSeek",
            ],
            "play-state": ["PlaybackStatus"],
            "repeat-mode": ["LoopStatus", "Shuffle"],
            "volume": ["Volume"],
            "position": ["Position"],
            "duration": ["Metadata", "CanSeek"],
        }
        properties = property_map.get(pspec.name, [])
        if properties:
            self._emit_properties_changed(properties)

    def _on_playlist_changed(self, *_args):
        if not self._connection:
            return
        self._emit_properties_changed(
            ["CanGoNext", "CanGoPrevious", "CanPlay", "CanPause", "CanSeek"]
        )

    def _emit_properties_changed(self, property_names: list[str]):
        changed = {
            property_name: self._player_property(property_name)
            for property_name in property_names
        }
        self._connection.emit_signal(
            None,
            MPRIS_OBJECT_PATH,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            GLib.Variant(
                "(sa{sv}as)",
                ("org.mpris.MediaPlayer2.Player", changed, []),
            ),
        )

    def _emit_seeked(self):
        if not self._connection:
            return
        self._connection.emit_signal(
            None,
            MPRIS_OBJECT_PATH,
            "org.mpris.MediaPlayer2.Player",
            "Seeked",
            GLib.Variant("(x)", (self._player.props.position * 1_000_000,)),
        )
