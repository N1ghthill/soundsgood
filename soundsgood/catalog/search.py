# Copyright 2025 SoundsGood developers
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import unicodedata


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).strip()


def rank_fields(fields, query: str) -> int | None:
    normalized_fields = [normalize(field) for field in fields if field]
    for offset, predicate in (
        (0, lambda field: field == query),
        (10, lambda field: field.startswith(query)),
        (20, lambda field: query in field),
    ):
        for index, field in enumerate(normalized_fields):
            if predicate(field):
                return offset + index
    return None
