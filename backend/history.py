"""Saved chat history for logged-in customers (the existing chat_messages table).

Table (unchanged from the original database):
    chat_messages(id INTEGER PK, user_id INTEGER NOT NULL -> users.id, role TEXT,
                  content TEXT, products_json TEXT NULL, created_at TEXT DEFAULT now)

Every function takes the user_id from the login session (main.py passes the
id from the signed cookie), and every query filters on it, so one customer can
never read or write another customer's messages. Guests are never saved.

products_json formats:
    new rows:    {"label": "hoodies", "products": [{"product_id", "name", "price"}, ...]}
                 a snapshot of what was shown, for the record
    older rows:  [{"product_id": ..., "name": ..., "price": ..., ...}, ...]
                 (written by the earlier HW4 app)
Either way, cards are rebuilt from the live catalogue on reload, so prices are
current and links still work.
"""

from __future__ import annotations

import json

from db import connect_readonly, connect_readwrite, product_summaries
from models import ChatReply, ChatTurn, HistoryMessage, SearchResults

HISTORY_PAGE = 100  # messages returned to the chat panel
AGENT_HISTORY = 20  # recent messages given to the agent
LEGACY_LABEL = "products from this chat"


def save_turn(user_id: int, user_message: str, reply: ChatReply) -> None:
    """Store one exchange: the customer's message and the bot's reply (with its products)."""
    products_json = None
    if reply.search:
        products_json = json.dumps(
            {
                "label": reply.search.label,
                "products": [
                    {"product_id": p.product_id, "name": p.name, "price": p.price} for p in reply.search.products
                ],
            }
        )
    with connect_readwrite() as con:  # one transaction: both rows or neither
        con.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_message),
        )
        con.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply.message, products_json),
        )


def _parse_products(products_json: str | None) -> tuple[str, list[str]] | None:
    """(label, product_ids) from either stored format, or None."""
    if not products_json:
        return None
    try:
        data = json.loads(products_json)
    except ValueError:
        return None
    if isinstance(data, dict):
        label, items = data.get("label") or LEGACY_LABEL, data.get("products") or []
    elif isinstance(data, list):
        label, items = LEGACY_LABEL, data
    else:
        return None
    ids = [i["product_id"] for i in items if isinstance(i, dict) and isinstance(i.get("product_id"), str)]
    return (label, ids) if ids else None


def _recent_rows(user_id: int, limit: int):
    with connect_readonly() as con:
        rows = con.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_history(user_id: int, limit: int = HISTORY_PAGE) -> list[HistoryMessage]:
    """The customer's most recent messages, oldest first, with product cards rebuilt live."""
    messages = []
    for r in _recent_rows(user_id, limit):
        if r["role"] not in ("user", "assistant"):
            continue
        search = None
        parsed = _parse_products(r["products_json"])
        if parsed:
            label, ids = parsed
            cards = product_summaries(ids)  # live name/price/image; dropped if no longer sold
            if cards:
                search = SearchResults(label=label, products=cards)
        messages.append(
            HistoryMessage(id=r["id"], role=r["role"], content=r["content"], search=search, created_at=r["created_at"])
        )
    return messages


def agent_history(user_id: int, limit: int = AGENT_HISTORY) -> list[ChatTurn]:
    """Recent turns for the agent. Replies that showed products get a short note
    listing them, so "the first one" still makes sense in a later visit."""
    turns = []
    for r in _recent_rows(user_id, limit):
        if r["role"] not in ("user", "assistant"):
            continue
        content = r["content"]
        parsed = _parse_products(r["products_json"]) if r["role"] == "assistant" else None
        if parsed:
            label, ids = parsed
            content += f"\n[Products shown for '{label}': {', '.join(ids[:12])}{' …' if len(ids) > 12 else ''}]"
        turns.append(ChatTurn(role=r["role"], content=content[:8000]))
    return turns
