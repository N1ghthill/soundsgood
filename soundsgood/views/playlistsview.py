# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

"""Adaptive browser and editor for persistent local playlists."""

from __future__ import annotations

from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk

from soundsgood.models import Playlist, PlaylistEntry
from soundsgood.widgets.playlistrows import (
    create_entry_factory,
    create_playlist_factory,
)
from soundsgood.widgets.songrow import set_accessible_label


class PlaylistsView(Adw.Bin):
    """Create, import, edit, play, and export saved playlists."""

    def __init__(self, application):
        super().__init__()
        self._app = application
        self._library = application.props.library
        self._player = application.props.player
        self._manager = application.props.playlist_manager
        self._selected_playlist = None
        self._detail_handlers = []
        self._compact = False

        self._split_view = Adw.NavigationSplitView()
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)

        create_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._name_entry = Gtk.Entry()
        self._name_entry.set_hexpand(True)
        self._name_entry.set_placeholder_text(_("New playlist"))
        self._name_entry.connect("activate", self._create_playlist)
        create_box.append(self._name_entry)
        create_button = Gtk.Button(icon_name="list-add-symbolic")
        create_button.add_css_class("suggested-action")
        create_button.add_css_class("compact-icon")
        create_button.set_tooltip_text(_("Create playlist"))
        set_accessible_label(create_button, _("Create playlist"))
        create_button.connect("clicked", self._create_playlist)
        create_box.append(create_button)
        import_button = Gtk.Button(icon_name="document-open-symbolic")
        import_button.add_css_class("flat")
        import_button.add_css_class("compact-icon")
        import_button.set_tooltip_text(_("Import playlist"))
        set_accessible_label(import_button, _("Import playlist"))
        import_button.connect("clicked", self._import_playlist)
        create_box.append(import_button)
        sidebar.append(create_box)

        self._selection = Gtk.SingleSelection.new(self._manager.props.playlists)
        self._selection.set_autoselect(False)
        self._selection.set_can_unselect(True)
        self._selection.connect("notify::selected-item", self._selection_changed)
        self._list = Gtk.ListView.new(self._selection, create_playlist_factory())
        self._list.set_single_click_activate(True)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self._list)
        sidebar.append(scroller)
        self._sidebar_status = Gtk.Label()
        self._sidebar_status.set_wrap(True)
        self._sidebar_status.add_css_class("dim-label")
        sidebar.append(self._sidebar_status)

        self._detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._detail.set_margin_top(12)
        self._detail.set_margin_bottom(12)
        self._detail.set_margin_start(12)
        self._detail.set_margin_end(12)
        self._detail_status = Gtk.Label(label=_("Select or create a playlist"))
        self._detail_status.set_halign(Gtk.Align.CENTER)
        self._detail_status.set_valign(Gtk.Align.CENTER)
        self._detail_status.set_vexpand(True)
        self._detail_status.add_css_class("dim-label")
        self._detail.append(self._detail_status)

        self._split_view.set_sidebar(Adw.NavigationPage.new(sidebar, _("Playlists")))
        self._split_view.set_content(Adw.NavigationPage.new(self._detail, _("Playlist")))
        self.set_child(self._split_view)

        self._manager_handlers = [
            self._manager.connect("loaded", self._manager_loaded),
            self._manager.connect("changed", self._manager_changed),
            self._manager.connect("error", self._manager_error),
        ]
        self._update_sidebar_status()

    def do_unroot(self):
        self._disconnect_detail_handlers()
        for handler_id in self._manager_handlers:
            if self._manager.handler_is_connected(handler_id):
                self._manager.disconnect(handler_id)
        self._manager_handlers.clear()
        Adw.Bin.do_unroot(self)

    def set_compact(self, compact: bool):
        self._compact = compact
        self._split_view.set_collapsed(compact)
        if compact and self._selected_playlist is None:
            self._split_view.set_show_content(False)
        elif not compact:
            self._split_view.set_show_content(True)
        if self._selected_playlist is not None:
            self._show_playlist(self._selected_playlist)

    def _manager_loaded(self, *_args):
        self._update_sidebar_status()
        if self._manager.props.playlists.get_n_items() and self._selection.get_selected_item() is None:
            self._selection.set_selected(0)

    def _manager_changed(self, _manager, _playlist):
        self._update_sidebar_status()

    def _manager_error(self, _manager, message):
        self._notify(message)
        self._sidebar_status.set_label(message)

    def _update_sidebar_status(self):
        count = self._manager.props.playlists.get_n_items()
        if not self._manager.props.loaded:
            message = _("Loading playlists...")
        elif count == 0:
            message = _("No saved playlists")
        else:
            message = ""
        self._sidebar_status.set_label(message)

    def _selection_changed(self, selection, _pspec):
        playlist = selection.get_selected_item()
        if playlist is None:
            self._clear_detail()
            self._selected_playlist = None
            self._detail.append(self._detail_status)
            if self._compact:
                self._split_view.set_show_content(False)
            return
        self._show_playlist(playlist)
        if self._compact:
            self._split_view.set_show_content(True)

    def _show_playlist(self, playlist: Playlist):
        self._clear_detail()
        self._selected_playlist = playlist
        if self._compact:
            back = Gtk.Button(icon_name="go-previous-symbolic")
            back.add_css_class("flat")
            back.add_css_class("compact-icon")
            back.set_halign(Gtk.Align.START)
            back.set_tooltip_text(_("Back to playlists"))
            set_accessible_label(back, _("Back to playlists"))
            back.connect("clicked", lambda *_args: self._split_view.set_show_content(False))
            self._detail.append(back)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.add_css_class("detail-header")
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        labels.set_hexpand(True)
        self._detail_title = Gtk.Label(label=playlist.props.name, xalign=0)
        self._detail_title.set_wrap(True)
        self._detail_title.add_css_class("title-2")
        labels.append(self._detail_title)
        self._detail_count = Gtk.Label(
            label=_n_songs(playlist.props.entry_count),
            xalign=0,
        )
        self._detail_count.add_css_class("dim-label")
        labels.append(self._detail_count)
        header.append(labels)

        self._play_button = Gtk.Button(
            label=_("Play"),
            icon_name="media-playback-start-symbolic",
        )
        self._play_button.add_css_class("suggested-action")
        self._play_button.add_css_class("compact-pill")
        self._play_button.set_valign(Gtk.Align.CENTER)
        self._play_button.connect("clicked", lambda *_args: self._play_playlist())
        header.append(self._play_button)

        add = Gtk.Button(icon_name="list-add-symbolic")
        add.add_css_class("flat")
        add.add_css_class("compact-icon")
        add.set_valign(Gtk.Align.CENTER)
        add.set_tooltip_text(_("Add songs from library"))
        set_accessible_label(add, _("Add songs from library"))
        add.connect("clicked", self._add_library_songs)
        header.append(add)

        delete = Gtk.Button(icon_name="edit-delete-symbolic")
        delete.add_css_class("flat")
        delete.add_css_class("compact-icon")
        delete.add_css_class("destructive-action")
        delete.set_valign(Gtk.Align.CENTER)
        delete.set_tooltip_text(_("Delete playlist"))
        set_accessible_label(delete, _("Delete playlist"))
        delete.connect("clicked", self._delete_playlist)
        header.append(delete)

        menu_button = Gtk.MenuButton(icon_name="view-more-symbolic")
        menu_button.add_css_class("flat")
        menu_button.add_css_class("compact-icon")
        menu_button.set_valign(Gtk.Align.CENTER)
        menu_button.set_tooltip_text(_("Playlist actions"))
        set_accessible_label(menu_button, _("Playlist actions"))
        menu_button.set_popover(self._create_actions_popover())
        header.append(menu_button)
        self._detail.append(header)

        self._entries_stack = Gtk.Stack()
        self._entries_stack.set_vexpand(True)
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        empty.set_halign(Gtk.Align.CENTER)
        empty.set_valign(Gtk.Align.CENTER)
        empty_icon = Gtk.Image(icon_name="view-list-symbolic")
        empty_icon.set_pixel_size(48)
        empty_icon.add_css_class("dim-label")
        empty.append(empty_icon)
        empty_label = Gtk.Label(label=_("This playlist is empty"))
        empty_label.add_css_class("title-3")
        empty.append(empty_label)
        empty_hint = Gtk.Label(
            label=_("Add songs from your library or import local audio files."),
        )
        empty_hint.set_wrap(True)
        empty_hint.set_justify(Gtk.Justification.CENTER)
        empty_hint.add_css_class("dim-label")
        empty.append(empty_hint)
        empty_add = Gtk.Button(
            label=_("Add Songs"),
            icon_name="list-add-symbolic",
        )
        empty_add.add_css_class("suggested-action")
        empty_add.add_css_class("compact-pill")
        empty_add.set_halign(Gtk.Align.CENTER)
        empty_add.connect("clicked", self._add_library_songs)
        empty.append(empty_add)
        self._entries_stack.add_named(empty, "empty")
        selection = Gtk.NoSelection.new(playlist.props.entries)
        self._entries_list = Gtk.ListView.new(
            selection,
            create_entry_factory(self._play_entry, self._move_entry, self._remove_entry),
        )
        self._entries_list.set_single_click_activate(False)
        self._entries_list.connect("activate", self._entry_activated)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self._entries_list)
        self._entries_stack.add_named(scroller, "entries")
        self._detail.append(self._entries_stack)
        self._detail_handlers = [
            playlist.connect("notify::name", self._sync_detail_header),
            playlist.connect("notify::entry-count", self._sync_detail_header),
        ]
        self._sync_detail_header()

    def _create_actions_popover(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        for label, icon, callback in (
            (_("Rename"), "document-edit-symbolic", self._rename_playlist),
            (_("Add Audio Files"), "document-open-symbolic", self._add_files),
            (_("Export M3U8"), "document-save-symbolic", self._export_playlist),
        ):
            button = Gtk.Button(label=label, icon_name=icon)
            button.add_css_class("flat")
            button.set_halign(Gtk.Align.FILL)
            button.connect("clicked", callback)
            box.append(button)
        popover = Gtk.Popover()
        popover.set_child(box)
        return popover

    def _sync_detail_header(self, *_args):
        playlist = self._selected_playlist
        if playlist is None or not hasattr(self, "_detail_title"):
            return
        self._detail_title.set_label(playlist.props.name)
        self._detail_count.set_label(_n_songs(playlist.props.entry_count))
        self._play_button.set_sensitive(playlist.props.entry_count > 0)
        self._entries_stack.set_visible_child_name(
            "entries" if playlist.props.entry_count else "empty"
        )

    def _create_playlist(self, _widget):
        name = self._name_entry.get_text().strip()
        if not name:
            self._notify(_("Enter a playlist name"))
            return
        try:
            playlist = self._manager.create(name)
        except ValueError as error:
            self._notify(str(error))
            return
        self._name_entry.set_text("")
        self._selection.set_selected(self._manager.props.playlists.get_n_items() - 1)
        self._notify(_("Created playlist %s") % playlist.props.name)

    def _import_playlist(self, _button):
        dialog = Gtk.FileDialog(title=_("Import Playlist"))
        dialog.set_filters(_playlist_filters())
        dialog.open(self.get_root(), None, self._import_selected)

    def _import_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except Exception:
            return
        self._manager.import_async(file, self._library, self._import_finished)

    def _import_finished(self, playlist, error):
        if error:
            self._notify(str(error))
            return
        self._selection.set_selected(self._manager.props.playlists.get_n_items() - 1)
        self._notify(_("Imported playlist %s") % playlist.props.name)

    def _add_library_songs(self, _button):
        playlist = self._selected_playlist
        if playlist is None:
            return
        if self._library.props.songs.get_n_items() == 0:
            self._notify(_("Your music library is empty"))
            return
        from soundsgood.widgets.playlistchooser import PlaylistSongChooserDialog

        dialog = PlaylistSongChooserDialog(self._app, playlist)
        dialog.present(self.get_root())

    def _add_files(self, _button):
        if self._selected_playlist is None:
            return
        dialog = Gtk.FileDialog(title=_("Add Audio Files"))
        dialog.set_filters(_audio_filters())
        dialog.open_multiple(self.get_root(), None, self._files_selected)

    def _files_selected(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
        except Exception:
            return
        self._manager.add_files_async(
            self._selected_playlist,
            files,
            self._library,
            self._files_added,
        )

    def _files_added(self, added, error):
        if error:
            self._notify(str(error))
        elif added:
            self._notify(_("Added %d songs") % added)
        else:
            self._notify(_("No playable local songs were selected"))

    def _rename_playlist(self, *_args):
        playlist = self._selected_playlist
        if playlist is None:
            return
        entry = Gtk.Entry(text=playlist.props.name)
        entry.set_activates_default(True)
        dialog = Adw.AlertDialog(heading=_("Rename Playlist"))
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("rename", _("Rename"))
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")

        def chosen(alert, result):
            if alert.choose_finish(result) != "rename":
                return
            try:
                self._manager.rename(playlist, entry.get_text())
            except ValueError as error:
                self._notify(str(error))
                return
            self._notify(_("Renamed playlist to %s") % playlist.props.name)

        dialog.choose(self.get_root(), None, chosen)

    def _delete_playlist(self, *_args):
        playlist = self._selected_playlist
        if playlist is None:
            return
        dialog = Adw.AlertDialog(
            heading=_("Delete %s?") % playlist.props.name,
            body=_("This removes the saved playlist, not the music files."),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def chosen(alert, result):
            if alert.choose_finish(result) != "delete":
                return
            self._delete_confirmed(playlist)

        dialog.choose(self.get_root(), None, chosen)

    def _delete_confirmed(self, playlist):
        model = self._manager.props.playlists
        position = next(
            (
                index
                for index in range(model.get_n_items())
                if model.get_item(index) is playlist
            ),
            -1,
        )
        if position < 0:
            return
        self._disconnect_detail_handlers()
        self._selected_playlist = None
        try:
            self._manager.delete(playlist)
        except ValueError as error:
            self._notify(str(error))
            return
        remaining = model.get_n_items()
        if remaining:
            self._selection.set_selected(min(position, remaining - 1))
        else:
            self._selection.unselect_all()
            self._clear_detail()
            self._detail.append(self._detail_status)
            if self._compact:
                self._split_view.set_show_content(False)
        self._update_sidebar_status()
        self._notify(_("Deleted playlist %s") % playlist.props.name)

    def _export_playlist(self, *_args):
        playlist = self._selected_playlist
        if playlist is None:
            return
        dialog = Gtk.FileDialog(title=_("Export Playlist"))
        dialog.set_initial_name(_safe_filename(playlist.props.name) + ".m3u8")
        dialog.save(self.get_root(), None, self._export_selected)

    def _export_selected(self, dialog, result):
        try:
            file = dialog.save_finish(result)
        except Exception:
            return
        path = file.get_path()
        if path:
            self._manager.export_async(
                self._selected_playlist,
                Path(path),
                self._export_finished,
            )

    def _export_finished(self, error):
        self._notify(str(error) if error else _("Playlist exported"))

    def _play_playlist(self):
        playlist = self._selected_playlist
        if playlist is None:
            return
        songs = self._manager.resolved_songs(playlist, self._library)
        if songs:
            self._player.play_song(songs[0], songs)
        else:
            self._notify(_("This playlist has no available songs"))

    def _play_entry(self, entry: PlaylistEntry):
        playlist = self._selected_playlist
        if playlist is None:
            return
        songs = self._manager.resolved_songs(playlist, self._library)
        song = next((item for item in songs if item.props.url == entry.props.url), None)
        if song is not None:
            self._player.play_song(song, songs)

    def _entry_activated(self, _list, position):
        if self._selected_playlist is None:
            return
        entry = self._selected_playlist.props.entries.get_item(position)
        if entry is not None and entry.props.available:
            self._play_entry(entry)

    def _entry_index(self, entry):
        entries = self._selected_playlist.props.entries
        for index in range(entries.get_n_items()):
            if entries.get_item(index) is entry:
                return index
        return -1

    def _move_entry(self, entry, step):
        position = self._entry_index(entry)
        target = position + step
        count = self._selected_playlist.props.entry_count
        if 0 <= position < count and 0 <= target < count:
            self._manager.move_entry(self._selected_playlist, position, target)

    def _remove_entry(self, entry):
        position = self._entry_index(entry)
        if position >= 0:
            self._manager.remove_entry(self._selected_playlist, position)

    def _clear_detail(self):
        self._disconnect_detail_handlers()
        child = self._detail.get_first_child()
        while child:
            self._detail.remove(child)
            child = self._detail.get_first_child()

    def _disconnect_detail_handlers(self):
        playlist = self._selected_playlist
        if playlist is not None:
            for handler_id in self._detail_handlers:
                if playlist.handler_is_connected(handler_id):
                    playlist.disconnect(handler_id)
        self._detail_handlers.clear()

    def _notify(self, message):
        window = self._app.props.window
        if window is not None:
            window.show_message(message)


def _playlist_filters():
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    supported = Gtk.FileFilter(name=_("Playlists"))
    for suffix in ("*.m3u", "*.m3u8", "*.pls"):
        supported.add_pattern(suffix)
    filters.append(supported)
    return filters


def _audio_filters():
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    audio = Gtk.FileFilter(name=_("Audio files"))
    for suffix in ("*.mp3", "*.flac", "*.ogg", "*.oga", "*.opus", "*.wav", "*.m4a", "*.aac", "*.wma"):
        audio.add_pattern(suffix)
    filters.append(audio)
    return filters


def _n_songs(count: int) -> str:
    return _("%d song") % count if count == 1 else _("%d songs") % count


def _safe_filename(name: str) -> str:
    return "".join("_" if character in "/\\\0" else character for character in name).strip() or "playlist"
