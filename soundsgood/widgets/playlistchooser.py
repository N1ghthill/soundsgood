# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Small adaptive dialog for adding library content to a saved playlist."""

from __future__ import annotations

from gettext import gettext as _
import unicodedata

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Pango

from soundsgood.widgets.songrow import set_accessible_label


class PlaylistChooserDialog(Adw.Dialog):
    def __init__(
        self,
        application,
        songs,
        description: str = "",
        focus_new=False,
    ):
        super().__init__(title=_("Add to Playlist"))
        self.set_content_width(390)
        self.set_content_height(480)
        self._app = application
        self._manager = application.props.playlist_manager
        self._songs = list(songs)
        self._description = description
        self._manager_handlers = [
            self._manager.connect("loaded", self._sync_status),
        ]

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        if description:
            label = Gtk.Label(label=description, xalign=0)
            label.set_wrap(True)
            label.add_css_class("dim-label")
            content.append(label)

        create_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_hexpand(True)
        self._name_entry.set_placeholder_text(_("New playlist name"))
        self._name_entry.connect("activate", self._create_playlist)
        create_box.append(self._name_entry)
        create_button = Gtk.Button(icon_name="list-add-symbolic")
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("compact-icon")
        create_button.set_tooltip_text(_("Create playlist"))
        set_accessible_label(create_button, _("Create playlist"))
        create_button.connect("clicked", self._create_playlist)
        create_box.append(create_button)
        content.append(create_box)

        self._selection = Gtk.SingleSelection.new(self._manager.props.playlists)
        self._selection.set_autoselect(False)
        self._selection.set_can_unselect(True)
        self._list = Gtk.ListView.new(
            self._selection,
            _create_chooser_factory(self._playlist_activated),
        )
        self._list.add_css_class("boxed-list")
        self._list.set_single_click_activate(True)
        self._list.connect("activate", self._playlist_position_activated)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self._list)
        content.append(scroller)

        self._status = Gtk.Label()
        self._status.set_wrap(True)
        self._status.add_css_class("dim-label")
        content.append(self._status)

        toolbar.set_content(content)
        self.set_child(toolbar)
        self._sync_status()
        if focus_new:
            self._name_entry.grab_focus()

    def do_unroot(self):
        for handler_id in self._manager_handlers:
            if self._manager.handler_is_connected(handler_id):
                self._manager.disconnect(handler_id)
        self._manager_handlers.clear()
        Adw.Dialog.do_unroot(self)

    def _sync_status(self, *_args):
        model = self._manager.props.playlists
        if not self._manager.props.loaded:
            self._status.set_label(_("Loading playlists..."))
        elif model.get_n_items() == 0:
            self._status.set_label(_("Create your first playlist above."))
        else:
            self._status.set_label("")

    def _playlist_position_activated(self, _list, position):
        self._playlist_activated(self._manager.props.playlists.get_item(position))

    def _playlist_activated(self, playlist):
        if playlist is None:
            return
        try:
            added = self._manager.add_songs(playlist, self._songs)
        except ValueError as error:
            self._status.set_label(str(error))
            return
        if added:
            self._notify(_("Added %d songs to %s") % (added, playlist.props.name))
            self.close()
        else:
            self._status.set_label(
                _("These songs are already in %s.") % playlist.props.name
            )

    def _create_playlist(self, _widget):
        name = self._name_entry.get_text().strip()
        if not name:
            self._status.set_label(_("Enter a playlist name."))
            return
        try:
            playlist = self._manager.create(name, self._songs)
        except ValueError as error:
            self._status.set_label(str(error))
            return
        self._notify(_("Created playlist %s") % playlist.props.name)
        self.close()

    def _notify(self, message: str):
        window = self._app.props.window
        if window is not None:
            window.show_message(message)


class PlaylistSongChooserDialog(Adw.Dialog):
    """Search and select library songs to append to one saved playlist."""

    def __init__(self, application, playlist):
        super().__init__(title=_("Add Songs"))
        self.set_content_width(620)
        self.set_content_height(620)
        self._app = application
        self._manager = application.props.playlist_manager
        self._playlist = playlist
        self._query = ""
        self._existing_urls = self._playlist_urls()

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        heading = Gtk.Label(
            label=_("Choose songs from your library for %s") % playlist.props.name,
            xalign=0,
        )
        heading.set_wrap(True)
        heading.add_css_class("heading")
        content.append(heading)

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(_("Search songs, artists, or albums"))
        self._search.connect("search-changed", self._search_changed)
        content.append(self._search)

        self._filter = Gtk.CustomFilter.new(self._matches_song)
        self._filtered = Gtk.FilterListModel.new(
            application.props.library.props.songs,
            self._filter,
        )
        self._selection = Gtk.MultiSelection.new(self._filtered)
        self._list = Gtk.ListView.new(
            self._selection,
            _create_song_picker_factory(self._selection),
        )
        self._list.add_css_class("boxed-list")
        self._list.set_single_click_activate(False)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self._list)
        content.append(scroller)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._status = Gtk.Label(xalign=0)
        self._status.set_hexpand(True)
        self._status.set_ellipsize(Pango.EllipsizeMode.END)
        self._status.add_css_class("dim-label")
        footer.append(self._status)
        select_all = Gtk.Button(label=_("Select All"))
        select_all.add_css_class("flat")
        select_all.connect("clicked", lambda *_args: self._selection.select_all())
        footer.append(select_all)
        add = Gtk.Button(label=_("Add Selected"), icon_name="list-add-symbolic")
        add.add_css_class("suggested-action")
        add.connect("clicked", self._add_selected)
        footer.append(add)
        content.append(footer)

        toolbar.set_content(content)
        self.set_child(toolbar)
        self._selection_handler = self._selection.connect(
            "selection-changed",
            self._sync_status,
        )
        self._filtered_handler = self._filtered.connect(
            "items-changed",
            self._sync_status,
        )
        self._playlist_handler = playlist.connect(
            "notify::entry-count",
            self._playlist_changed,
        )
        self._sync_status()

    def do_unroot(self):
        if self._selection_handler and self._selection.handler_is_connected(
            self._selection_handler
        ):
            self._selection.disconnect(self._selection_handler)
        self._selection_handler = 0
        if self._filtered_handler and self._filtered.handler_is_connected(
            self._filtered_handler
        ):
            self._filtered.disconnect(self._filtered_handler)
        self._filtered_handler = 0
        if self._playlist_handler and self._playlist.handler_is_connected(
            self._playlist_handler
        ):
            self._playlist.disconnect(self._playlist_handler)
        self._playlist_handler = 0
        Adw.Dialog.do_unroot(self)

    def _search_changed(self, entry):
        self._query = _search_key(entry.get_text())
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._sync_status()

    def _matches_song(self, song):
        if song.props.url in self._existing_urls:
            return False
        if not self._query:
            return True
        haystack = _search_key(
            " ".join(
                (
                    song.props.title,
                    song.props.artist,
                    song.props.album,
                    song.props.album_artist,
                )
            )
        )
        return self._query in haystack

    def _playlist_urls(self):
        entries = self._playlist.props.entries
        return {
            entries.get_item(position).props.url
            for position in range(entries.get_n_items())
        }

    def _playlist_changed(self, *_args):
        self._existing_urls = self._playlist_urls()
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._sync_status()

    def _selected_songs(self):
        return [
            self._filtered.get_item(position)
            for position in range(self._filtered.get_n_items())
            if self._selection.is_selected(position)
        ]

    def _sync_status(self, *_args):
        selected = self._selection.get_selection().get_size()
        available = self._filtered.get_n_items()
        if available == 0:
            message = (
                _("No matching songs")
                if self._query
                else _("All library songs are already in this playlist")
            )
        elif selected:
            message = _("%d selected") % selected
        else:
            message = _("Select one or more songs")
        self._status.set_label(message)

    def _add_selected(self, _button):
        songs = self._selected_songs()
        if not songs:
            self._status.set_label(_("Select one or more songs"))
            return
        try:
            added = self._manager.add_songs(self._playlist, songs)
        except ValueError as error:
            self._status.set_label(str(error))
            return
        if not added:
            self._status.set_label(
                _("The selected songs are already in this playlist")
            )
            return
        window = self._app.props.window
        if window is not None:
            window.show_message(
                _("Added %d songs to %s") % (added, self._playlist.props.name)
            )
        self.close()


def _n_songs(count: int) -> str:
    return _("%d song") % count if count == 1 else _("%d songs") % count


def _search_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).casefold()


class _SongPickerItem(Gtk.Box):
    def __init__(self, selection):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._selection = selection
        self._list_item = None
        self._selected_handler = 0
        self._syncing = False
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self._check = Gtk.CheckButton()
        self._check.set_valign(Gtk.Align.CENTER)
        self._check.connect("toggled", self._toggled)
        self.append(self._check)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._title = Gtk.Label(xalign=0)
        self._title.set_ellipsize(Pango.EllipsizeMode.END)
        self._title.add_css_class("heading")
        labels.append(self._title)
        self._context = Gtk.Label(xalign=0)
        self._context.set_ellipsize(Pango.EllipsizeMode.END)
        self._context.add_css_class("caption")
        self._context.add_css_class("dim-label")
        labels.append(self._context)
        self.append(labels)

    def bind(self, list_item, song):
        self.unbind()
        self._list_item = list_item
        self._selected_handler = list_item.connect("notify::selected", self._sync)
        self._title.set_label(song.props.title)
        self._context.set_label(
            " — ".join(part for part in (song.props.artist, song.props.album) if part)
        )
        set_accessible_label(self, _("Select %s") % song.props.title)
        self._sync()

    def unbind(self):
        if self._list_item is not None and self._selected_handler:
            if self._list_item.handler_is_connected(self._selected_handler):
                self._list_item.disconnect(self._selected_handler)
        self._selected_handler = 0
        self._list_item = None

    def _sync(self, *_args):
        if self._list_item is None:
            return
        self._syncing = True
        self._check.set_active(self._list_item.get_selected())
        self._syncing = False

    def _toggled(self, button):
        if self._syncing or self._list_item is None:
            return
        position = self._list_item.get_position()
        if button.get_active():
            self._selection.select_item(position, False)
        else:
            self._selection.unselect_item(position)


def _create_song_picker_factory(selection):
    factory = Gtk.SignalListItemFactory()
    factory.connect(
        "setup",
        lambda _factory, item: item.set_child(_SongPickerItem(selection)),
    )
    factory.connect(
        "bind",
        lambda _factory, item: item.get_child().bind(item, item.get_item()),
    )
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory


class _PlaylistChooserItem(Gtk.Box):
    def __init__(self, on_activate):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._playlist = None
        self._handlers = []
        self._on_activate = on_activate
        self.set_margin_top(7)
        self.set_margin_bottom(7)
        self.set_margin_start(10)
        self.set_margin_end(10)

        icon = Gtk.Image(icon_name="audio-x-generic-symbolic")
        icon.set_pixel_size(28)
        self.append(icon)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        self._name = Gtk.Label(xalign=0)
        self._name.set_ellipsize(Pango.EllipsizeMode.END)
        self._name.add_css_class("heading")
        labels.append(self._name)
        self._count = Gtk.Label(xalign=0)
        self._count.add_css_class("caption")
        self._count.add_css_class("dim-label")
        labels.append(self._count)
        self.append(labels)
        button = Gtk.Button(icon_name="list-add-symbolic")
        button.add_css_class("flat")
        button.add_css_class("compact-icon")
        button.set_valign(Gtk.Align.CENTER)
        button.set_tooltip_text(_("Add to this playlist"))
        set_accessible_label(button, _("Add to this playlist"))
        button.connect("clicked", lambda *_args: self._activate())
        self.append(button)

    def bind(self, playlist):
        self.unbind()
        self._playlist = playlist
        self._handlers = [
            playlist.connect("notify::name", self._sync),
            playlist.connect("notify::entry-count", self._sync),
        ]
        self._sync()

    def unbind(self):
        if self._playlist is not None:
            for handler_id in self._handlers:
                if self._playlist.handler_is_connected(handler_id):
                    self._playlist.disconnect(handler_id)
        self._handlers.clear()
        self._playlist = None

    def _sync(self, *_args):
        if self._playlist is None:
            return
        self._name.set_label(self._playlist.props.name)
        self._count.set_label(_n_songs(self._playlist.props.entry_count))

    def _activate(self):
        if self._playlist is not None:
            self._on_activate(self._playlist)


def _create_chooser_factory(on_activate):
    factory = Gtk.SignalListItemFactory()
    factory.connect(
        "setup",
        lambda _factory, item: item.set_child(_PlaylistChooserItem(on_activate)),
    )
    factory.connect("bind", lambda _factory, item: item.get_child().bind(item.get_item()))
    factory.connect("unbind", lambda _factory, item: item.get_child().unbind())
    return factory
