# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


class PreferencesDialog:
    """Small wrapper around Adw.PreferencesDialog."""

    def __init__(self, application):
        self._app = application
        self._settings = application.props.settings
        self._parent = None

        self._dialog = Adw.PreferencesDialog()
        self._dialog.set_title(_("Preferences"))

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=_("Music Library"))

        self._folder_row = Adw.ActionRow(
            title=_("Music Folder"),
            subtitle=self._settings.get_string("music-dir") or _("Default: ~/Music"),
        )
        button = Gtk.Button(label=_("Select"))
        button.connect("clicked", self._on_select_folder)
        self._folder_row.add_suffix(button)
        self._folder_row.set_activatable_widget(button)
        group.add(self._folder_row)

        page.add(group)
        self._dialog.add(page)

    def present(self, parent):
        self._parent = parent
        self._dialog.present(parent)

    def _on_select_folder(self, _button):
        dialog = Gtk.FileDialog(title=_("Select Music Folder"))
        dialog.select_folder(self._parent, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except Exception:
            return

        path = folder.get_path()
        if not path:
            return

        self._settings.set_string("music-dir", path)
        self._folder_row.set_subtitle(path)
        self._app.props.library.scan(path)
