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
        appearance_group = Adw.PreferencesGroup(title=_("Appearance"))

        self._theme_model = Gtk.StringList.new([_("Light"), _("Dark")])
        self._theme_dropdown = Gtk.DropDown(model=self._theme_model)
        current_scheme = self._settings.get_string("color-scheme")
        self._theme_dropdown.set_selected(1 if current_scheme == "dark" else 0)
        self._theme_dropdown.connect("notify::selected", self._on_theme_selected)

        theme_row = Adw.ActionRow(
            title=_("Theme"),
            subtitle=_("Use the selected theme instead of the system setting"),
        )
        theme_row.add_suffix(self._theme_dropdown)
        theme_row.set_activatable_widget(self._theme_dropdown)
        appearance_group.add(theme_row)
        page.add(appearance_group)

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

    def _on_theme_selected(self, dropdown, _param):
        scheme = "dark" if dropdown.get_selected() == 1 else "light"
        self._settings.set_string("color-scheme", scheme)
        self._app.apply_color_scheme()
