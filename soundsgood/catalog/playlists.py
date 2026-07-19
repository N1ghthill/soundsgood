# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations


def m3u_entries(text: str) -> list[str]:
    return [
        entry
        for line in text.splitlines()
        if (entry := line.strip()) and not entry.startswith("#")
    ]


def pls_entries(text: str) -> list[str]:
    entries = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key.casefold().startswith("file"):
            continue
        suffix = key[4:]
        value = value.strip()
        if suffix.isdigit() and value:
            entries[int(suffix)] = value
    return [entries[index] for index in sorted(entries)]
