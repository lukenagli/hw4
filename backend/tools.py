"""Tools the shop assistant can call.

Every tool opens the database read-only, uses parameterized queries for any
value that came from the conversation, and returns a Pydantic model from
models.py (never a loose string or dict).

    search_catalogue(query, ...)     browse a type of item  -> CatalogueSearchResult (shown on the page)
    find_alternatives(id, size)      size sold out          -> AlternativesResult (shown as chat cards)
    find_products(query)             what the shopper said  -> ProductSearchResult
    get_product_details(product_id)  one product            -> ProductDetails | ProductNotFound
    check_stock(product_id, size)    stock, all or one size -> StockReport | ProductNotFound
"""

from __future__ import annotations

import json
import re
import sqlite3

from catalogue import garment_category
from db import SIZE_ORDER, SIZE_RANK, connect_readonly, image_url
from pydantic_ai import RunContext

from models import (
    AlternativeHit,
    AlternativesResult,
    CatalogueHit,
    CatalogueSearchResult,
    ChatDeps,
    ProductDetails,
    ProductMatch,
    ProductNotFound,
    ProductSearchResult,
    SearchFilters,
    SizeStockLevel,
    StockReport,
)

MAX_RESULTS = 8

# Garment categories live in catalogue.py (shared with the API and filters).

# What shoppers type -> the category it means.
CATEGORY_WORDS = {
    "hoodie": "hoodie", "hoody": "hoodie", "hood": "hoodie", "hooded": "hoodie",
    "tee": "t-shirt", "tshirt": "t-shirt", "shirt": "t-shirt",
    "crewneck": "crewneck", "crew": "crewneck", "mockneck": "crewneck",
    "quarterzip": "quarter-zip", "qzip": "quarter-zip",
    "jacket": "jacket", "coat": "jacket",
    # Style words such as "bomber" or "fleece" are left out on purpose: they match
    # by name and tags, so "bomber jacket" finds the one bomber, not every jacket.
}

# Shopper phrases rewritten before splitting into words.
PHRASES = [
    (r"\bt[- ]?shirts?\b", " tshirt "),
    (r"\b(1/4|1 4|quarter)[- ]?zips?\b", " quarterzip "),
    (r"\bcrew[- ]?necks?\b", " crewneck "),
    (r"\bhoodies\b", " hoodie "),
    (r"\b(short|long)[- ]sleeves?\b", r" \1sleeve "),
    (r"\bhandsome dan\b", " bulldog "),
]

# Words that carry no product meaning in a shopping question.
STOPWORDS = {
    "a", "about", "an", "and", "any", "anything", "are", "available", "can", "do", "does", "find",
    "for", "get", "got", "have", "how", "i", "im", "in", "is", "it", "item", "items", "like",
    "looking", "many", "me", "much", "my", "need", "of", "on", "one", "ones", "or", "please",
    "price", "show", "sell", "size", "sizes", "some", "something", "stock", "that", "the",
    "there", "this", "those", "to", "u", "want", "what", "whats", "which", "with", "you",
    "your", "yale", "left", "cost", "costs", "still", "thing", "stuff",
    "gear", "merch", "apparel", "clothes", "clothing", "options", "products", "product",
}


def _stem(word: str) -> str:
    # hoodies -> hoodie, tees -> tee, crewnecks -> crewneck (but not "dress" -> "dres")
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _normalize(text: str) -> str:
    text = text.lower()
    for pattern, repl in PHRASES:
        text = re.sub(pattern, repl, text)
    return text


def _words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", _normalize(text))}


def query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for w in re.findall(r"[a-z0-9]+", _normalize(query)):
        if w in STOPWORDS or len(w) < 2:
            continue
        w = _stem(w)
        if w not in terms:
            terms.append(w)
    return terms


# --- Sizes ------------------------------------------------------------------------

SIZE_ALIASES = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS", "xsm": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "md": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "lrg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL", "xlg": "XL", "1xl": "XL",
    "xxl": "XXL", "2xl": "XXL", "2x": "XXL", "xxlarge": "XXL", "2xlarge": "XXL",
    "extraextralarge": "XXL", "doublexl": "XXL", "doubleextralarge": "XXL",
}


def normalize_size(size: str) -> str | None:
    """'large' -> 'L', '2XL' -> 'XXL', 'extra small' -> 'XS'. None if not a size we carry."""
    key = re.sub(r"[^a-z0-9]", "", size.lower())
    return SIZE_ALIASES.get(key)


# --- Database helpers ---------------------------------------------------------------


def _catalogue_row(con: sqlite3.Connection, product_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()


def _stock_levels(con: sqlite3.Connection, product_id: str) -> list[SizeStockLevel]:
    rows = con.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    rows = sorted(rows, key=lambda r: SIZE_RANK.get(r["size"], len(SIZE_ORDER)))
    return [SizeStockLevel(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0) for r in rows]


def _not_found(product_id: str) -> ProductNotFound:
    return ProductNotFound(
        product_id=product_id,
        message="No product has this id. Use find_products with the shopper's words to get a real id.",
    )


# --- Tools --------------------------------------------------------------------------


# --- Catalogue search (results go on the page) ------------------------------------

MAX_PAGE_RESULTS = 30  # safety cap: most products one search can return (largest category, crewnecks, has 29)


def _matches_strictly(term: str, row: sqlite3.Row, category: str) -> bool:
    """Does this product match one search word?

    Garment words ("hoodies", "tees", "crewnecks", "jackets") match by cleaned-up
    category only, so "hoodies" finds every hoodie-type label and "crewnecks"
    doesn't pull in a "crew-neck t-shirt". Every other word must appear in the
    name, garment type, colors or search tags.
    """
    wanted = CATEGORY_WORDS.get(term)
    if wanted:
        return category == wanted
    fields = " ".join(
        [row["name"], row["garment_type"], " ".join(json.loads(row["colors"])), " ".join(json.loads(row["search_tags"]))]
    )
    return term in _words(fields)


def search_catalogue(
    ctx: RunContext[ChatDeps],
    query: str,
    max_price: float | None = None,
    min_price: float | None = None,
    size: str | None = None,
) -> CatalogueSearchResult:
    """Search the catalogue for a TYPE of item, to show the matches on the website.

    Use this when the shopper is browsing ("what hoodies do you have?", "show me
    navy crewnecks under $60", "bulldog stuff in medium"). Every word in `query`
    must match (name, garment type, colors or tags). Put prices and sizes in the
    filter arguments, not in `query`. `query` may be empty when a filter is set
    ("anything under $40?", "what's in stock in XL?").

    Args:
        query: The kind of item in the shopper's words, without prices or sizes, e.g. "navy crewneck".
        max_price: Only items at or below this price in dollars, e.g. 60 for "under $60".
        min_price: Only items at or above this price in dollars.
        size: Only items in stock in this size, as the shopper said it ("medium", "2XL").
    """
    terms = query_terms(query)
    wanted_size = normalize_size(size) if size else None
    filters = SearchFilters(
        min_price=min_price,
        max_price=max_price,
        size=wanted_size,
        size_asked=size,
        size_recognized=None if size is None else wanted_size is not None,
    )

    hits: list[tuple[int, CatalogueHit]] = []
    unmatched: list[str] = []
    has_filter = max_price is not None or min_price is not None or wanted_size is not None
    if (terms or has_filter) and not (size and wanted_size is None):
        with connect_readonly() as con:
            rows = con.execute("SELECT * FROM catalogue").fetchall()
            stock = {
                (r["product_id"], r["size"]): r["quantity"]
                for r in con.execute("SELECT product_id, size, quantity FROM inventory")
            }
        matched_any: set[str] = set()
        for row in rows:
            category = garment_category(row["garment_type"])
            ok = [t for t in terms if _matches_strictly(t, row, category)]
            matched_any.update(ok)
            if len(ok) != len(terms):
                continue
            if max_price is not None and row["price"] > max_price:
                continue
            if min_price is not None and row["price"] < min_price:
                continue
            pid = row["product_id"]
            if wanted_size:
                in_stock = stock.get((pid, wanted_size), 0) > 0
                if not in_stock:
                    continue
            else:
                in_stock = any(stock.get((pid, s), 0) > 0 for s in SIZE_ORDER)
            # Rank: how many words hit the name (most specific first), then name.
            rank = sum(t in _words(row["name"]) for t in terms)
            hits.append((rank, CatalogueHit(
                product_id=pid,
                name=row["name"],
                category=category,
                price=row["price"],
                colors=json.loads(row["colors"]),
                in_stock=in_stock,
            )))
        unmatched = [t for t in terms if t not in matched_any]

    hits.sort(key=lambda h: (-h[0], h[1].name))
    products = [h for _, h in hits][:MAX_PAGE_RESULTS]

    # Remember what this search returned: the backend only puts these ids on the page.
    ids = [p.product_id for p in products]
    ctx.deps.showable_ids.update(ids)
    ctx.deps.last_search_ids = ids
    ctx.deps.last_search_total = len(hits)

    return CatalogueSearchResult(
        query=query, filters=filters, total_matches=len(hits), products=products, unmatched_terms=unmatched
    )


PRICE_WINDOW = 20.0  # "similar price": within this many dollars of the original
MAX_ALTERNATIVES = 6
MIN_IN_WINDOW = 3  # fewer than this in the window -> widen to the whole category


def find_alternatives(ctx: RunContext[ChatDeps], product_id: str, size: str) -> AlternativesResult | ProductNotFound:
    """Find similar products that DO have a size in stock, for when the shopper's choice is sold out.

    Call this whenever a size the shopper wants is sold out (check_stock shows
    quantity 0). Returns products in the same category at a similar price
    (within $20; the whole category if that finds fewer than 3) that have the
    size in stock, closest price first. Show them as cards with
    results_kind="alternatives".

    Args:
        product_id: The sold-out product's exact product_id.
        size: The size the shopper wants, as they said it ("XL", "large", "2XL").
    """
    wanted = normalize_size(size)
    with connect_readonly() as con:
        original = _catalogue_row(con, product_id)
        if original is None:
            return _not_found(product_id)
        category = garment_category(original["garment_type"])
        price = original["price"]
        window = f"${price - PRICE_WINDOW:.2f} to ${price + PRICE_WINDOW:.2f}"
        if wanted is None:
            return AlternativesResult(
                original_product_id=original["product_id"], original_name=original["name"], category=category,
                original_price=price, size_asked=size, size=None, original_quantity_in_size=None,
                price_window=window, widened=False, alternatives=[],
            )
        own = con.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (original["product_id"], wanted)
        ).fetchone()
        rows = con.execute(
            "SELECT c.*, i.quantity FROM catalogue c JOIN inventory i ON i.product_id = c.product_id "
            "WHERE i.size = ? AND i.quantity > 0 AND c.product_id <> ?",
            (wanted, original["product_id"]),
        ).fetchall()

    same_category = [r for r in rows if garment_category(r["garment_type"]) == category]
    in_window = [r for r in same_category if abs(r["price"] - price) <= PRICE_WINDOW]
    widened = len(in_window) < MIN_IN_WINDOW
    pool = same_category if widened else in_window
    pool.sort(key=lambda r: (abs(r["price"] - price), -r["quantity"], r["name"]))
    picked = pool[:MAX_ALTERNATIVES]

    alternatives = [
        AlternativeHit(
            product_id=r["product_id"],
            name=r["name"],
            category=category,
            price=r["price"],
            colors=json.loads(r["colors"]),
            in_stock=True,
            quantity_in_size=r["quantity"],
            price_difference=round(r["price"] - price, 2),
        )
        for r in picked
    ]
    ids = [a.product_id for a in alternatives]
    ctx.deps.showable_ids.update(ids)
    ctx.deps.last_search_ids = ids
    return AlternativesResult(
        original_product_id=original["product_id"],
        original_name=original["name"],
        category=category,
        original_price=price,
        size_asked=size,
        size=wanted,
        original_quantity_in_size=own["quantity"] if own else None,
        price_window=window,
        widened=widened,
        alternatives=alternatives,
    )


def find_products(query: str, max_results: int = MAX_RESULTS) -> ProductSearchResult:
    """Turn what the shopper said into catalogue products.

    Use this first whenever a shopper names or describes a product ("the Champion
    hoodie", "that Harvard game shirt", "navy crewneck"). Matches the shopper's
    words against product names, garment types (cleaned into categories) and
    search tags, plus colors.

    Read `status`: single = use it; multiple = ask which one (or list if browsing);
    partial = no exact match, offer these as the closest; none = we don't carry it.

    Args:
        query: The shopper's description, in their words.
        max_results: How many matches to return (1 to 8).
    """
    terms = query_terms(query)
    max_results = max(1, min(max_results, MAX_RESULTS))
    if not terms:
        return ProductSearchResult(query=query, status="none", total_matches=0, matches=[], unmatched_terms=[])

    with connect_readonly() as con:
        rows = con.execute("SELECT * FROM catalogue").fetchall()

    scored: list[tuple[int, int, sqlite3.Row, list[str], str]] = []
    for row in rows:
        category = garment_category(row["garment_type"])
        name = _words(row["name"])
        tags = _words(" ".join(json.loads(row["search_tags"])))
        garment = _words(row["garment_type"])
        colors = _words(" ".join(json.loads(row["colors"])))

        matched, score = [], 0
        for t in terms:
            points = 0
            if CATEGORY_WORDS.get(t) == category:
                points += 3
            if t in name:
                points += 3
            if t in tags:
                points += 2
            if t in garment:
                points += 2
            if t in colors:
                points += 1
            if points:
                matched.append(t)
                score += points
        if matched:
            scored.append((len(matched), score, row, matched, category))

    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["name"]))
    all_matched = {t for _, _, _, m, _ in scored for t in m}
    unmatched = [t for t in terms if t not in all_matched]

    full = [s for s in scored if s[0] == len(terms)]
    if len(full) == 1:
        status, picked = "single", full
    elif full:
        status, picked = "multiple", full
    elif scored:
        status, picked = "partial", scored
    else:
        status, picked = "none", []

    matches = [
        ProductMatch(
            product_id=row["product_id"],
            name=row["name"],
            category=category,
            garment_type=row["garment_type"],
            colors=json.loads(row["colors"]),
            price=row["price"],
            image_url=image_url(row["image_file_path"]),
            matched_terms=m,
        )
        for _, _, row, m, category in picked[:max_results]
    ]
    return ProductSearchResult(
        query=query, status=status, total_matches=len(picked), matches=matches, unmatched_terms=unmatched
    )


def get_product_details(product_id: str) -> ProductDetails | ProductNotFound:
    """Get the description, price, colors and which sizes are in stock for one product.

    Args:
        product_id: An exact product_id from find_products.
    """
    with connect_readonly() as con:
        row = _catalogue_row(con, product_id)
        if row is None:
            return _not_found(product_id)
        levels = _stock_levels(con, row["product_id"])
    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        category=garment_category(row["garment_type"]),
        garment_type=row["garment_type"],
        description=row["description"],
        price=row["price"],
        colors=json.loads(row["colors"]),
        image_url=image_url(row["image_file_path"]),
        sizes_in_stock=[s.size for s in levels if s.in_stock],
        sold_out_sizes=[s.size for s in levels if not s.in_stock],
    )


def check_stock(product_id: str, size: str | None = None) -> StockReport | ProductNotFound:
    """Get live stock for one product: every size, plus one size if the shopper asked.

    Args:
        product_id: An exact product_id from find_products.
        size: Optional size as the shopper said it, e.g. "large", "2XL", "medium", "XS".
    """
    with connect_readonly() as con:
        row = _catalogue_row(con, product_id)
        if row is None:
            return _not_found(product_id)
        levels = _stock_levels(con, row["product_id"])

    requested = normalize_size(size) if size else None
    level = next((s for s in levels if s.size == requested), None)
    return StockReport(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        stock_by_size=levels,
        total_in_stock=sum(s.quantity for s in levels),
        sizes_in_stock=[s.size for s in levels if s.in_stock],
        sold_out_sizes=[s.size for s in levels if not s.in_stock],
        size_asked=size,
        size_recognized=None if size is None else requested is not None,
        requested_size=requested,
        requested_quantity=level.quantity if level else None,
        requested_in_stock=level.in_stock if level else None,
    )


ALL_TOOLS = [search_catalogue, find_alternatives, find_products, get_product_details, check_stock]
