"""Append-only audit trail of every agent run: output/audit_trail.json.

The file is one JSON array; each element is one run of the agent (one chat
message). Guarantees:

  * Append-only: existing entries are always read back and kept; the file is
    never cleared, including across server restarts.
  * Always valid JSON: each write goes to a temp file that then atomically
    replaces the old one (os.replace), so a crash mid-write can't leave half
    a file. If the existing file is ever unreadable, it is renamed aside
    (never deleted) and a new array is started.
  * Safe with concurrent chats: a thread lock (same process) plus an OS file
    lock on audit_trail.json.lock (other processes) serialize writers.
  * Short and public-safe: strings are truncated, and emails, card numbers
    and passwords are scrubbed. Customers appear only as "guest" or
    "user:<id>". Password hashes and API keys never reach this module.
"""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from db import PROJECT_DIR
from safety import scrub_emails, scrub_sensitive

AUDIT_PATH = PROJECT_DIR / "output" / "audit_trail.json"
LOCK_PATH = AUDIT_PATH.with_suffix(".json.lock")
MAX_TEXT = 160  # characters kept from any argument, result or message

_thread_lock = threading.Lock()


# --- helpers ----------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def short(value: Any, limit: int = MAX_TEXT) -> str:
    """Compact, scrubbed, truncated text for the log."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    text = scrub_emails(scrub_sensitive(" ".join(text.split()))[0])
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarize_result(content: Any) -> str:
    """One-line summary of a tool result (key facts, not the whole object)."""
    if isinstance(content, BaseModel):
        d = content.model_dump(mode="json")
        if "requested_quantity" in d:  # StockReport
            stock = " ".join(f"{s['size']}={s['quantity']}" for s in d.get("stock_by_size", []))
            asked = f"; asked {d['size_asked']} -> {d['requested_quantity']}" if d.get("size_asked") else ""
            return short(f"{d['product_id']} ${d['price']:.2f} {stock}{asked}")
        if "alternatives" in d:  # AlternativesResult
            alts = ", ".join(f"{a['product_id']}({d['size']}={a['quantity_in_size']})" for a in d["alternatives"])
            return short(f"{d['original_product_id']} {d['size']}={d['original_quantity_in_size']}; alternatives: {alts or 'none'}")
        if "total_matches" in d and "products" in d:  # CatalogueSearchResult
            return short(f"{d['total_matches']} match(es), returned {len(d['products'])}: " + ", ".join(p["product_id"] for p in d["products"][:6]))
        if "status" in d and "matches" in d:  # ProductSearchResult
            return short(f"{d['status']}, {d['total_matches']} match(es): " + ", ".join(m["product_id"] for m in d["matches"][:6]))
        if "description" in d:  # ProductDetails
            return short(f"{d['product_id']} ${d['price']:.2f} in stock: {','.join(d['sizes_in_stock'])}")
        if d.get("found") is False:  # ProductNotFound
            return short(f"not found: {d['product_id']}")
    return short(content)


def steps_from_messages(messages: list[ModelMessage]) -> list[dict]:
    """Each step of the agent loop, in order: model turns, tool calls and results, retries."""
    steps: list[dict] = []
    calls: dict[str, dict] = {}
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    if part.tool_name == "final_result" or part.tool_name.startswith("final_result"):
                        steps.append({"time": msg.timestamp.isoformat(timespec="seconds"), "type": "answer_draft",
                                      "text": short(part.args_as_dict().get("message", ""))})
                        continue
                    step = {"time": msg.timestamp.isoformat(timespec="seconds"), "type": "tool_call",
                            "tool": part.tool_name, "args": short(part.args_as_dict()), "result": None}
                    calls[part.tool_call_id] = step
                    steps.append(step)
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                    calls[part.tool_call_id]["result"] = _summarize_result(part.content)
                elif isinstance(part, RetryPromptPart):
                    reason = part.content if isinstance(part.content, str) else json.dumps(part.content, default=str)
                    kind = "fact_check_retry" if "Fact check failed" in reason else (
                        "safety_retry" if "Safety check failed" in reason else "retry")
                    steps.append({"time": part.timestamp.isoformat(timespec="seconds"), "type": kind, "detail": short(reason)})
    for i, s in enumerate(steps, 1):
        s["step"] = i
    return steps


# --- locked append ---------------------------------------------------------------------


@contextmanager
def _file_lock():
    """Cross-process lock: exclusive lock on a 1-byte region of a lock file."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "a+b") as fh:
        if os.name == "nt":
            import msvcrt

            fh.seek(0)
            for _ in range(200):  # up to ~10 s
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            else:
                raise TimeoutError("audit trail lock busy")
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _read_existing() -> list:
    if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except ValueError:
        pass
    # Unreadable: keep it (renamed), never delete, and start a fresh array.
    AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.unreadable-{int(time.time())}.json"))
    return []


def append_entry(entry: dict) -> None:
    """Add one run to the audit trail. Thread-safe and process-safe."""
    with _thread_lock, _file_lock():
        entries = _read_existing()
        entries.append(entry)
        tmp = AUDIT_PATH.with_name(f".audit_trail.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
        # Atomic: readers see the old or the new file, never half of one. Retry
        # briefly, because a sync client (OneDrive) can hold the file for a moment.
        for attempt in range(20):
            try:
                os.replace(tmp, AUDIT_PATH)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.1)
