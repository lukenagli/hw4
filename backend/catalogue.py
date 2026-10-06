"""Clean groupings for the catalogue's messy labels, shared by the API,
the Products page filters and the agent's tools."""

from __future__ import annotations

import re

# --- Garment categories -----------------------------------------------------------
# The catalogue has 22 inconsistent garment_type labels ("short-sleeve T-shirt",
# "t-shirt", "hooded sweatshirt", "pullover hoodie", ...). Each label is mapped
# to one clean category, checked in this order.

CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("hoodie", re.compile(r"hood")),
    ("quarter-zip", re.compile(r"quarter-zip")),
    ("jacket", re.compile(r"jacket")),
    ("long-sleeve shirt", re.compile(r"long-sleeve performance shirt")),
    ("t-shirt", re.compile(r"t-shirt")),
    ("crewneck", re.compile(r"crewneck|mockneck")),
]


def garment_category(garment_type: str) -> str:
    label = garment_type.lower()
    for category, pattern in CATEGORY_RULES:
        if pattern.search(label):
            return category
    return label


# --- Color families -----------------------------------------------------------------
# 22 raw color names ("navy", "navy blue", "heather gray", "dark heather charcoal",
# "dusty coral", ...) grouped into families a shopper would filter by. Checked in
# order, so "navy blue" is Navy, not Blue.

COLOR_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("Navy", re.compile(r"navy")),
    ("Gray", re.compile(r"gr[ae]y|charcoal")),
    ("White & Cream", re.compile(r"white|cream|ivory")),
    ("Blue", re.compile(r"blue")),
    ("Black", re.compile(r"black")),
    ("Red & Coral", re.compile(r"red|coral")),
    ("Gold & Yellow", re.compile(r"gold|yellow")),
    ("Green", re.compile(r"green")),
    ("Multicolor", re.compile(r"multi")),
]
COLOR_FAMILIES = [name for name, _ in COLOR_RULES]


def color_family(color: str) -> str | None:
    c = color.lower()
    return next((name for name, pattern in COLOR_RULES if pattern.search(c)), None)


def color_families(colors: list[str]) -> list[str]:
    found = {f for f in (color_family(c) for c in colors) if f}
    return [f for f in COLOR_FAMILIES if f in found]
