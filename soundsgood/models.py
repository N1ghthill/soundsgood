# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations
from enum import IntEnum
from typing import Optional
from gi.repository import GObject, Gio


class RepeatMode(IntEnum):
    """Player repeat mode."""
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class PlayState(IntEnum):
    """Playback state."""
    STOPPED = 0
    LOADING = 1
    PAUSED = 2
    PLAYING = 3


class LibraryState(IntEnum):
    """Library scan state."""
    EMPTY = 0
    SCANNING = 1
    READY = 2
    ERROR = 3


class Song(GObject.GObject):
    """Represents a single music track."""

    __gtype_name__ = "Song"

    title = GObject.Property(type=str, default="")
    artist = GObject.Property(type=str, default="")
    album = GObject.Property(type=str, default="")
    album_artist = GObject.Property(type=str, default="")
    duration = GObject.Property(type=int, default=0)
    track_number = GObject.Property(type=int, default=0)
    disc_number = GObject.Property(type=int, default=1)
    year = GObject.Property(type=str, default="")
    genre = GObject.Property(type=str, default="")
    url = GObject.Property(type=str, default="")
    thumbnail = GObject.Property(type=str, default=None)
    favorite = GObject.Property(type=bool, default=False)
    play_count = GObject.Property(type=int, default=0)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self.props, key, value)

    def __eq__(self, other):
        if isinstance(other, Song):
            return self.props.url == other.props.url
        return False

    def __hash__(self):
        return hash(self.props.url)

    def __repr__(self):
        return f"Song(title={self.props.title!r}, artist={self.props.artist!r})"


class Album(GObject.GObject):
    """Represents a music album."""

    __gtype_name__ = "Album"

    title = GObject.Property(type=str, default="")
    artist = GObject.Property(type=str, default="")
    year = GObject.Property(type=str, default="")
    duration = GObject.Property(type=int, default=0)
    song_count = GObject.Property(type=int, default=0)
    thumbnail = GObject.Property(type=str, default=None)
    songs = GObject.Property(type=object, default=None)  # Gio.ListStore

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self.props, key, value)

    def __repr__(self):
        return f"Album(title={self.props.title!r}, artist={self.props.artist!r})"


class Artist(GObject.GObject):
    """Represents a music artist."""

    __gtype_name__ = "Artist"

    name = GObject.Property(type=str, default="")
    song_count = GObject.Property(type=int, default=0)
    album_count = GObject.Property(type=int, default=0)
    thumbnail = GObject.Property(type=str, default=None)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self.props, key, value)

    def __repr__(self):
        return f"Artist(name={self.props.name!r})"
