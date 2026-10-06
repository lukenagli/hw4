"""SQLite access for data/campus_customs.db.

Paths are built from this file's location, so the app works no matter which
folder uvicorn is started from.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from catalogue import color_families, garment_category
from models import ProductSummary

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent  # repo root: .env, requirements.txt, data/, output/
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCTS_DIR = DATA_DIR / "products"

# Sizes in display order (alphabetical order would put XS after XL).
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_RANK = {size: i for i, size in enumerate(SIZE_ORDER)}


def connect_readonly() -> sqlite3.Connection:
    """For catalogue and stock reads. The site never edits products."""
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def connect_readwrite() -> sqlite3.Connection:
    """For account and chat writes. Foreign keys are off by default in SQLite."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def image_url(image_file_path: str) -> str:
    """image_file_path is relative to data/, e.g. "products/foo.jpg"."""
    return f"/media/{image_file_path}"


def product_summaries(product_ids: list[str] | None = None) -> list[ProductSummary]:
    """Card data straight from the database, plus the clean category, color
    families and in-stock sizes the Products page filters on.

    With no ids: the whole catalogue, sorted by name (the Products page).
    With ids: just those products, in the order given; unknown ids are dropped.
    """
    if product_ids is not None and not product_ids:
        return []
    with connect_readonly() as con:
        if product_ids is None:
            rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
            stock_rows = con.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
        else:
            marks = ",".join("?" * len(product_ids))
            found = con.execute(f"SELECT * FROM catalogue WHERE product_id IN ({marks})", product_ids).fetchall()
            by_id = {r["product_id"]: r for r in found}
            rows = [by_id[pid] for pid in dict.fromkeys(product_ids) if pid in by_id]
            stock_rows = con.execute(
                f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", product_ids
            ).fetchall()

    in_stock: dict[str, list[str]] = {}
    for r in stock_rows:
        if r["quantity"] > 0:
            in_stock.setdefault(r["product_id"], []).append(r["size"])

    summaries = []
    for r in rows:
        sizes = sorted(in_stock.get(r["product_id"], []), key=lambda s: SIZE_RANK.get(s, len(SIZE_ORDER)))
        summaries.append(
            ProductSummary(
                product_id=r["product_id"],
                name=r["name"],
                garment_type=r["garment_type"],
                description=r["description"],
                price=r["price"],
                image_url=image_url(r["image_file_path"]),
                in_stock=bool(sizes),
                category=garment_category(r["garment_type"]),
                color_families=color_families(json.loads(r["colors"])),
                sizes_in_stock=sizes,
            )
        )
    return summaries
