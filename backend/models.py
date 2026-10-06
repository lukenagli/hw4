"""Pydantic types shared by the API routes, the agent and its tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# --- Catalogue (REST routes) --------------------------------------------------


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    image_url: str
    in_stock: bool
    # Clean groupings for the Products page filters (see catalogue.py).
    category: str = ""
    color_families: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)


class ProductDetail(ProductSummary):
    colors: list[str]
    search_tags: list[str]
    inventory: list[SizeStock]


# --- Tool results (what the agent sees) -----------------------------------------
# Every tool returns one of these models, never a bare string or dict, so the
# model always gets the same named fields and the code can rely on them.

SizeCode = Literal["XS", "S", "M", "L", "XL", "XXL"]
MatchStatus = Literal["single", "multiple", "partial", "none"]


class ProductMatch(BaseModel):
    """One candidate from find_products: enough to tell similar items apart."""

    product_id: str = Field(description="Use this id with get_product_details and check_stock.")
    name: str
    category: str = Field(description="Cleaned-up garment category, e.g. 'hoodie', 't-shirt'.")
    garment_type: str = Field(description="The raw garment_type label from the catalogue.")
    colors: list[str]
    price: float = Field(description="Price in US dollars, from the catalogue.")
    image_url: str
    matched_terms: list[str] = Field(description="Which of the shopper's words this product matched.")


class ProductSearchResult(BaseModel):
    """Result of find_products.

    status:
      single   - exactly one product matches every word: use it.
      multiple - several products match every word: ask the shopper which one
                 (or list them if they are browsing).
      partial  - nothing matches every word; these are the closest matches.
                 Say there's no exact match before suggesting them.
      none     - nothing matched at all. Say the shop doesn't carry it.
    """

    query: str
    status: MatchStatus
    total_matches: int = Field(description="How many products matched, before trimming to max_results.")
    matches: list[ProductMatch]
    unmatched_terms: list[str] = Field(description="Shopper words that matched no product at all.")


class ProductDetails(BaseModel):
    """Full catalogue facts for one product (get_product_details)."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    price: float
    colors: list[str] = Field(description="Colors visible on this single colorway, not options to choose.")
    image_url: str
    sizes_in_stock: list[SizeCode]
    sold_out_sizes: list[SizeCode]


class SizeStockLevel(BaseModel):
    size: SizeCode
    quantity: int
    in_stock: bool


class StockReport(BaseModel):
    """Live stock for one product (check_stock).

    If a size was asked for, requested_size / requested_quantity /
    requested_in_stock answer it directly. If the size wasn't understood,
    size_recognized is False and requested_* are empty.
    """

    product_id: str
    name: str
    price: float
    stock_by_size: list[SizeStockLevel] = Field(description="All six sizes in XS..XXL order.")
    total_in_stock: int
    sizes_in_stock: list[SizeCode]
    sold_out_sizes: list[SizeCode]
    size_asked: str | None = Field(description="The size exactly as the shopper said it, if any.")
    size_recognized: bool | None = Field(description="None if no size was asked about.")
    requested_size: SizeCode | None
    requested_quantity: int | None
    requested_in_stock: bool | None


class ProductNotFound(BaseModel):
    """Returned when a product_id doesn't exist. Never guess a replacement."""

    product_id: str
    found: Literal[False] = False
    message: str


class CatalogueHit(BaseModel):
    """One product from search_catalogue, kept compact because there can be dozens."""

    product_id: str
    name: str
    category: str
    price: float
    colors: list[str]
    in_stock: bool = Field(description="True if any size is in stock (or the requested size, if a size filter was used).")


class SearchFilters(BaseModel):
    min_price: float | None
    max_price: float | None
    size: SizeCode | None = Field(description="Only products in stock in this size, if set.")
    size_asked: str | None = Field(description="Size as the shopper said it.")
    size_recognized: bool | None


class CatalogueSearchResult(BaseModel):
    """Result of search_catalogue: every product matching ALL the shopper's words and filters."""

    query: str
    filters: SearchFilters
    total_matches: int
    products: list[CatalogueHit] = Field(
        description="Best matches first, at most 30. If total_matches is larger, say you're showing the first ones."
    )
    unmatched_terms: list[str] = Field(description="Words no product matched; if any, there are no results.")


class AlternativeHit(CatalogueHit):
    quantity_in_size: int = Field(description="Units of the requested size in stock.")
    price_difference: float = Field(description="This price minus the original product's price.")


class AlternativesResult(BaseModel):
    """Result of find_alternatives: same-category products that have the size in stock."""

    original_product_id: str
    original_name: str
    category: str
    original_price: float
    size_asked: str
    size: SizeCode | None = Field(description="Normalized size; None if it isn't a size the shop carries.")
    original_quantity_in_size: int | None = Field(description="Units of the original in that size (0 = sold out).")
    price_window: str = Field(description="The 'similar price' range searched first, e.g. '$48.00 to $88.00'.")
    widened: bool = Field(description="True if too few matches were in the price window, so the whole category was used.")
    alternatives: list[AlternativeHit] = Field(description="Closest price first, at most 6. Empty means none have the size.")


class CustomerInfo(BaseModel):
    """The only account fields the agent ever sees. No id, no password hash."""

    first_name: str
    last_name: str
    email: str


PageType = Literal["home", "products", "product", "about", "login", "signup", "other"]


class PageContext(BaseModel):
    """What the shopper is looking at, sent by the browser with each message."""

    path: str = Field(default="/", max_length=200)
    page_type: PageType = "other"
    product_id: str | None = Field(default=None, max_length=120, description="Set on a single product page.")
    results_label: str | None = Field(
        default=None, max_length=120, description="Chat search results currently shown on the Products page."
    )


@dataclass
class ChatDeps:
    """Per-request context shared by the agent's instructions and tools.

    Built by the backend for every message. customer comes from the login
    session (never from the browser); page comes from the browser but its
    product_id is checked against the catalogue first.
    """

    user_id: int | None = None
    customer: CustomerInfo | None = None  # None means a guest
    page: PageContext = field(default_factory=PageContext)
    page_product_name: str | None = None  # catalogue name of page.product_id, if valid
    # Filled by search_catalogue / find_alternatives during a turn: only these
    # ids may be shown as product cards.
    showable_ids: set[str] = field(default_factory=set)
    # Filled by the fact check (factcheck.py) as the reply is validated.
    fact_check_retries: int = 0
    safety_retries: int = 0  # replies redone because they leaked internal details
    last_search_total: int = 0  # matches before the result cap, for "showing N of M"
    fact_check_prices: list[str] = field(default_factory=list)
    fact_check_stock: list[str] = field(default_factory=list)
    last_search_ids: list[str] = field(default_factory=list)


# --- Chat ---------------------------------------------------------------------

MAX_MESSAGE_CHARS = 1000  # safety: longest customer message accepted (422 otherwise)
MAX_HISTORY_MESSAGES = 20  # earlier turns given to the agent
MAX_HISTORY_ITEMS = 40  # most history items a guest's browser may send


class ChatTurn(BaseModel):
    """One earlier message in the conversation, as the website sends it."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    # Only used for guests. For logged-in customers the backend loads history
    # from chat_messages instead, so the browser can't rewrite it.
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_ITEMS)
    page: PageContext = Field(default_factory=PageContext)


class AgentReply(BaseModel):
    """What the model fills in. It only *chooses* products (by id); it never
    supplies names, prices or images. The backend turns this into ChatReply."""

    message: str = Field(
        description="Short, friendly reply for the chat bubble, in plain text. For searches, "
        "summarise (count plus a highlight or two); don't list every item."
    )
    results_label: str | None = Field(
        default=None,
        description="Only when showing search_catalogue results on the page: a short heading label "
        "in the shopper's terms, e.g. 'hoodies' or 'navy crewnecks under $60'. Otherwise null.",
    )
    result_product_ids: list[str] = Field(
        default_factory=list,
        description="Only with results_label: the product_ids from search_catalogue or "
        "find_alternatives to show, in display order. Leave empty to show every result of your last search.",
    )
    results_kind: Literal["search", "alternatives"] = Field(
        default="search",
        description="'search' for search_catalogue results (shown on the Products page); "
        "'alternatives' for find_alternatives results (shown as cards in the chat, page unchanged).",
    )


class SearchResults(BaseModel):
    """Products the website should show on the page as cards."""

    label: str = Field(description="Heading text, e.g. 'hoodies' -> 'Results for hoodies'.")
    kind: Literal["search", "alternatives"] = "search"
    total_matches: int = Field(default=0, description="Matches before the result cap (0 = same as len(products)).")
    products: list[ProductSummary] = Field(
        description="Built from the database on the backend: name, price, image, description, in_stock."
    )


class FactCheckSummary(BaseModel):
    """What the fact check verified in this reply (shown as a small badge in the chat)."""

    status: Literal["verified", "corrected", "no_figures", "unverified"] = Field(
        description="verified: all figures matched first time; corrected: the agent had to redo the "
        "answer, and the final one matched; no_figures: nothing to check; unverified: retries ran out."
    )
    prices: list[str] = Field(default_factory=list)
    stock: list[str] = Field(default_factory=list)
    retries: int = 0


class ChatReply(BaseModel):
    """What /api/chat returns: the chat text, plus page results when the agent ran a search."""

    message: str
    fact_check: FactCheckSummary | None = None
    search: SearchResults | None = Field(
        default=None,
        description="Set only when the agent searched the catalogue and found products. "
        "None for ordinary questions, so the page is left alone.",
    )


class HistoryMessage(BaseModel):
    """One saved message, as GET /api/chat/history returns it."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    search: SearchResults | None = Field(
        default=None, description="Products that came with this reply, rebuilt from the live catalogue."
    )
    created_at: str


class ChatHistory(BaseModel):
    messages: list[HistoryMessage]
