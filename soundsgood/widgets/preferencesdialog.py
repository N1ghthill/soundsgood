# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from soundsgood.diagnostics import diagnostics_file, get_logger


LOGGER = get_logger("preferences")


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

        self._theme_model = Gtk.StringList.new([_("System"), _("Light"), _("Dark")])
        self._theme_dropdown = Gtk.DropDown(model=self._theme_model)
        current_scheme = self._settings.get_string("color-scheme")
        theme_index = {"system": 0, "light": 1, "dark": 2}.get(current_scheme, 0)
        self._theme_dropdown.set_selected(theme_index)
        self._theme_dropdown.connect("notify::selected", self._on_theme_selected)

        theme_row = Adw.ActionRow(
            title=_("Theme"),
            subtitle=_("Use the selected theme instead of the system setting"),
        )
        theme_row.add_suffix(self._theme_dropdown)
        theme_row.set_activatable_widget(self._theme_dropdown)
        appearance_group.add(theme_row)
        page.add(appearance_group)

        playback_group = Adw.PreferencesGroup(title=_("Playback"))

        self._notifications_switch = Gtk.Switch()
        self._notifications_switch.set_valign(Gtk.Align.CENTER)
        self._notifications_switch.set_active(self._settings.get_boolean("enable-notifications"))
        self._notifications_switch.connect(
            "notify::active",
            self._on_notifications_toggled,
        )
        notifications_row = Adw.ActionRow(
            title=_("Track Notifications"),
            subtitle=_("Show a desktop notification when a new song starts"),
        )
        notifications_row.add_suffix(self._notifications_switch)
        notifications_row.set_activatable_widget(self._notifications_switch)
        playback_group.add(notifications_row)

        self._inhibit_switch = Gtk.Switch()
        self._inhibit_switch.set_valign(Gtk.Align.CENTER)
        self._inhibit_switch.set_active(self._settings.get_boolean("inhibit-suspend"))
        self._inhibit_switch.connect(
            "notify::active",
            self._on_inhibit_toggled,
        )
        inhibit_row = Adw.ActionRow(
            title=_("Prevent Suspend"),
            subtitle=_("Keep the session awake while music is playing"),
        )
        inhibit_row.add_suffix(self._inhibit_switch)
        inhibit_row.set_activatable_widget(self._inhibit_switch)
        playback_group.add(inhibit_row)

        page.add(playback_group)

        group = Adw.PreferencesGroup(title=_("Music Library"))

        self._folder_row = Adw.ActionRow(
            title=_("Music Folder"),
            subtitle=self._settings.get_string("music-dir") or _("Default: ~/Music"),
        )
        button = Gtk.Button(label=_("Select"))
        button.add_css_class("compact-pill")
        button.set_valign(Gtk.Align.CENTER)
        button.connect("clicked", self._on_select_folder)
        self._folder_row.add_suffix(button)
        self._folder_row.set_activatable_widget(button)
        group.add(self._folder_row)

        rescan_row = Adw.ActionRow(
            title=_("Reindex Library"),
            subtitle=_("Rescan the music folder and refresh file metadata"),
        )
        rescan_button = Gtk.Button(label=_("Rescan Now"))
        rescan_button.add_css_class("compact-pill")
        rescan_button.set_valign(Gtk.Align.CENTER)
        rescan_button.connect("clicked", self._on_rescan_library)
        rescan_row.add_suffix(rescan_button)
        rescan_row.set_activatable_widget(rescan_button)
        group.add(rescan_row)

        page.add(group)

        diagnostics_group = Adw.PreferencesGroup(title=_("Diagnostics"))
        diagnostics_row = Adw.ActionRow(
            title=_("Application Log"),
            subtitle=str(diagnostics_file()),
        )
        diagnostics_button = Gtk.Button(label=_("Open Folder"))
        diagnostics_button.add_css_class("compact-pill")
        diagnostics_button.set_valign(Gtk.Align.CENTER)
        diagnostics_button.connect("clicked", self._on_open_diagnostics)
        diagnostics_row.add_suffix(diagnostics_button)
        diagnostics_row.set_activatable_widget(diagnostics_button)
        diagnostics_group.add(diagnostics_row)
        page.add(diagnostics_group)
        self._dialog.add(page)

    def present(self, parent):
        self._parent = parent
        self._dialog.present(parent)

    def _on_select_folder(self, _button):
        self._app.select_music_folder(
            self._parent,
            on_selected=lambda path: self._folder_row.set_subtitle(path),
        )

    def _on_rescan_library(self, _button):
        self._app.reindex_library()

    def _on_theme_selected(self, dropdown, _param):
        scheme = ("system", "light", "dark")[dropdown.get_selected()]
        self._settings.set_string("color-scheme", scheme)
        self._app.apply_color_scheme()

    def _on_open_diagnostics(self, _button):
        try:
            Gio.AppInfo.launch_default_for_uri(
                diagnostics_file().parent.resolve().as_uri(),
                None,
            )
        except GLib.Error:
            LOGGER.exception("Could not open diagnostics folder")

    def _on_notifications_toggled(self, switch, _param):
        self._settings.set_boolean("enable-notifications", switch.get_active())
        if not switch.get_active():
            self._app.withdraw_notification("now-playing")

    def _on_inhibit_toggled(self, switch, _param):
        self._settings.set_boolean("inhibit-suspend", switch.get_active())
        self._app.sync_desktop_integration()
