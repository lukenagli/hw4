"""Fact check: every price and stock number in a reply must come from this turn's tools.

Runs as a PydanticAI output validator (see agent.py). Before a reply is sent,
it collects every value the database tools returned during this turn, then
checks the reply text:

  * prices: every "$68", "$68.00" or "$1,234.50"
  * stock numbers: any number next to stock words, e.g. "only 2 left",
    "25 in stock", "20 larges left", "15 in XXL", "0 available"

A price passes if a tool returned it this turn (as a price field or inside
text such as "$48.00 to $88.00"), if the customer typed it, or if it's a
simple combination of returned prices (2-10 of an item, or two items' sum or
difference). A stock number passes if it is a quantity, total or result count
a tool returned this turn (including the sum of quantities in one returned
list), a number in a returned product name, or a number the customer typed.

If anything fails, or the reply states figures without calling any tool, the
validator raises ModelRetry with the exact problem, and the agent rewrites
the answer, usually after calling the right tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart

PRICE_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
_WORDS = r"(?:[A-Za-z()'’\-/]+\s+){0,8}?"
# Digits that belong to a price ("$68.00") or a decimal are never stock counts.
NOT_PRICE = r"(?<![$\d.,])"
STOCK_PATTERNS = [
    # "25 in stock", "20 larges left", "25 Yale Mom Hoodies in size L (large) currently in stock"
    re.compile(NOT_PRICE + r"\b(\d{1,5})\s+" + _WORDS + r"(?:left|in\s+stock|available|remaining|units?|pieces?|on\s+hand)\b", re.I),
    # "only 2", "just 5"
    re.compile(r"\b(?:only|just)\s+(\d{1,5})\b", re.I),
    # "15 in XXL", "8 in size M", "12 in medium"
    re.compile(NOT_PRICE + r"\b(\d{1,5})\s+in\s+(?:size\s+)?(?:XXL|XL|XS|2XL|S|M|L|small|medium|large|extra[- ]large|extra[- ]small)\b", re.I),
    # "stock: 25", "quantity of 8"
    re.compile(r"\b(?:stock|quantity)\s*(?:of|is|:)?\s*(\d{1,5})\b", re.I),
]
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass
class TurnFacts:
    """Everything the tools returned this turn, flattened."""

    tools_called: list[str] = field(default_factory=list)
    prices: set[float] = field(default_factory=set)
    numbers: set[float] = field(default_factory=set)


@dataclass
class FactCheckResult:
    ok: bool
    problems: list[str]
    prices_checked: list[str]
    stock_checked: list[str]


# Which tool fields a stock figure may come from. Only real quantities and
# result counts count; incidental numbers (e.g. how many sizes are listed)
# don't, or "only 3 left" could pass because a product has 3 sizes in stock.
QUANTITY_KEYS = {"quantity", "requested_quantity", "total_in_stock", "quantity_in_size", "original_quantity_in_size", "total_matches"}
RESULT_LISTS = {"products", "matches", "alternatives"}
NAME_KEYS = {"name", "original_name", "query"}


def _walk(value: Any, facts: TurnFacts, key: str = "") -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, facts, str(k))
    elif isinstance(value, (list, tuple, set)):
        if key in RESULT_LISTS:
            facts.numbers.add(float(len(value)))  # "I found 8 hoodies available"
        # A total across one returned list, e.g. "96 XL units across these 6 hoodies".
        items = [v.model_dump() if isinstance(v, BaseModel) else v for v in value]
        for qkey in ("quantity", "quantity_in_size"):
            qs = [i[qkey] for i in items if isinstance(i, dict) and isinstance(i.get(qkey), int)]
            if len(qs) > 1:
                facts.numbers.add(float(sum(qs)))
        for v in value:
            _walk(v, facts, key)
    elif isinstance(value, bool):
        return
    elif isinstance(value, (int, float)):
        if "price" in key:
            facts.prices.add(round(abs(float(value)), 2))
        elif key in QUANTITY_KEYS:
            facts.numbers.add(float(value))
    elif isinstance(value, str):
        for m in PRICE_RE.finditer(value):
            facts.prices.add(_amount(m.group(1)))
        if key in NAME_KEYS:  # e.g. "2025 Yale Vs Harvard T Shirt"
            for m in NUMBER_RE.finditer(value):
                facts.numbers.add(float(m.group()))


def _amount(text: str) -> float:
    return round(float(text.replace(",", "")), 2)


def collect_facts(messages: list[ModelMessage]) -> TurnFacts:
    """Tool results in this run. Earlier turns are passed as plain text with no
    tool parts, so every ToolReturnPart here came from the current turn."""
    facts = TurnFacts()
    for msg in messages:
        if not isinstance(msg, ModelRequest):
            continue
        for part in msg.parts:
            if isinstance(part, ToolReturnPart):
                facts.tools_called.append(part.tool_name)
                _walk(part.content, facts)
    return facts


def _derived_prices(prices: set[float]) -> set[float]:
    """Simple arithmetic a shopper might ask for: quantities of one item, two items together, a difference."""
    base = sorted(p for p in prices if p > 0)
    out = set(base)
    for p in base:
        out.update(round(p * k, 2) for k in range(2, 11))
    for i, a in enumerate(base):
        for b in base[i + 1 :]:
            out.add(round(a + b, 2))
            out.add(round(abs(a - b), 2))
    return out


def check_reply(text: str, facts: TurnFacts, user_message: str = "") -> FactCheckResult:
    user_prices = {_amount(m.group(1)) for m in PRICE_RE.finditer(user_message)}
    user_numbers = {float(n) for n in NUMBER_RE.findall(user_message)}
    allowed_prices = _derived_prices(facts.prices) | user_prices
    allowed_numbers = facts.numbers | user_numbers | {0.0}

    problems: list[str] = []
    prices_checked: list[str] = []
    stock_checked: list[str] = []

    for m in PRICE_RE.finditer(text):
        amount = _amount(m.group(1))
        prices_checked.append(f"${amount:.2f}")
        if amount not in allowed_prices:
            problems.append(f"the price ${amount:.2f} was not returned by any tool this turn")

    seen: set[tuple[int, str]] = set()
    for pattern in STOCK_PATTERNS:
        for m in pattern.finditer(text):
            n = float(m.group(1))
            snippet = m.group(0).strip()
            if (m.start(1), m.group(1)) in seen:
                continue
            seen.add((m.start(1), m.group(1)))
            stock_checked.append(snippet)
            if n not in allowed_numbers:
                problems.append(f'the stock figure "{snippet}" ({int(n)}) does not match any quantity a tool returned this turn')

    if (prices_checked or stock_checked) and not facts.tools_called:
        problems.insert(0, "you stated prices or stock numbers without calling any tool this turn")

    return FactCheckResult(ok=not problems, problems=problems, prices_checked=prices_checked, stock_checked=stock_checked)


def retry_message(result: FactCheckResult, facts: TurnFacts) -> str:
    known = ", ".join(f"${p:.2f}" for p in sorted(facts.prices)) or "none"
    return (
        "Fact check failed before sending your reply: "
        + "; ".join(result.problems)
        + f". Prices the tools returned this turn: {known}. Call the right tool "
        "(get_product_details for prices, check_stock for quantities) and answer only with "
        "numbers from tool results. If you don't have the number, say so instead of estimating."
    )
