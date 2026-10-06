"""Safety rules enforced in code (the prompt states them too; this backs them up).

  * scrub_sensitive(text): removes payment card numbers and passwords from a
    customer message before the model sees it, before it is saved to
    chat_messages, and before it is written to the audit trail.
  * scrub_emails(text, allowed): hides any email address except the
    logged-in customer's own (used on replies and in the audit trail).
  * leak_problems(reply): finds internal details in a reply (tool names,
    database tables, chunks of the system prompt) so the agent must redo it.
"""

from __future__ import annotations

import re

# 13-19 digits, optionally grouped by spaces or dashes: the shape of a card number.
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
# "password: hunter2", "my password is hunter2", "pw=hunter2"
_PASSWORD_RE = re.compile(r"\b(pass(?:word|code)?|pwd|pw)\b(\s*(?:is|:|=)\s*|\s+)(\S+)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def scrub_sensitive(text: str) -> tuple[str, list[str]]:
    """Remove card numbers and passwords. Returns (clean text, what was removed)."""
    removed: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            removed.append("card_number")
            return "[card number removed]"
        return m.group()

    text = _CARD_RE.sub(card, text)

    def password(m: re.Match) -> str:
        removed.append("password")
        return f"{m.group(1)}{m.group(2)}[removed]"

    text = _PASSWORD_RE.sub(password, text)
    return text, removed


def scrub_emails(text: str, allowed: str | None = None) -> str:
    """Hide every email address except `allowed` (the logged-in customer's own)."""
    keep = (allowed or "").lower()
    return EMAIL_RE.sub(lambda m: m.group() if keep and m.group().lower() == keep else "[email hidden]", text)


# --- Internal-detail leak check ----------------------------------------------------

INTERNAL_TERMS = [
    "search_catalogue", "find_alternatives", "find_products", "get_product_details", "check_stock",
    "ChatDeps", "AgentReply", "results_label", "result_product_ids", "results_kind", "product_summaries",
    "chat_messages", "password_hash", "campus_customs.db", "sqlite", "pydantic", "portkey",
    "system prompt", "prompt.md",
]
_INTERNAL_RE = re.compile("|".join(re.escape(t) for t in INTERNAL_TERMS), re.I)
_TABLE_RE = re.compile(r"\b(catalogue|inventory|users)\s+(table|schema|column)s?\b", re.I)
_WORD_RE = re.compile(r"[a-z0-9']+")
NGRAM = 16  # a run of 16 words copied from the prompt counts as leaking it (shorter runs are ordinary shop phrases)


def _ngrams(words: list[str], n: int = NGRAM) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


class LeakGuard:
    """Built once from the system prompt text."""

    def __init__(self, prompt: str):
        self._prompt_ngrams = _ngrams(_WORD_RE.findall(prompt.lower()))

    def problems(self, reply: str) -> list[str]:
        found: list[str] = []
        terms = sorted({m.group().lower() for m in _INTERNAL_RE.finditer(reply)})
        if terms:
            found.append(f"it mentions internal names ({', '.join(terms)})")
        if _TABLE_RE.search(reply):
            found.append("it describes the database structure")
        if _ngrams(_WORD_RE.findall(reply.lower())) & self._prompt_ngrams:
            found.append("it repeats wording from your instructions")
        return found
