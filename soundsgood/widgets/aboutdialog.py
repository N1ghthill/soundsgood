# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


class AboutDialog:
    """Small wrapper around Adw.AboutDialog."""

    def __init__(self, version: str):
        self._dialog = Adw.AboutDialog(
            application_name="SoundsGood",
            application_icon="io.github.irving.soundsgood",
            developer_name="SoundsGood Developers",
            version=version,
            comments="A local music player for GNOME.",
            website="https://github.com/irving/soundsgood",
            issue_url="https://github.com/irving/soundsgood/issues",
            license_type=Gtk.License.GPL_2_0,
        )

    def present(self, parent):
        self._dialog.present(parent)
