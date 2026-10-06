"""Offline tests for the audit trail and the code-enforced loop limits (no API calls).

Uses a temporary audit file, so the real output/audit_trail.json is untouched.
Run from the project folder:  .venv/Scripts/python tests/test_audit.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import audit  # noqa: E402
from agent import MAX_MODEL_REQUESTS, run_chat, shop_agent  # noqa: E402
from models import ChatDeps  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

tmp = Path(tempfile.mkdtemp())
audit.AUDIT_PATH = tmp / "audit_trail.json"
audit.LOCK_PATH = tmp / "audit_trail.json.lock"


def entries() -> list:
    return json.loads(audit.AUDIT_PATH.read_text(encoding="utf-8"))


def test_append_only_and_concurrency() -> None:
    audit.append_entry({"note": "pre-existing entry"})
    threads = [
        threading.Thread(target=lambda t=t: [audit.append_entry({"thread": t, "n": i}) for i in range(25)])
        for t in range(8)
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    data = entries()  # json.loads raises if the file were ever corrupted
    assert data[0] == {"note": "pre-existing entry"}, "existing entries must be kept"
    assert len(data) == 1 + 8 * 25, len(data)
    print(f"  concurrency: 8 threads x 25 appends -> {len(data)} entries, valid JSON, first entry kept")


def test_scrubbing() -> None:
    s = audit.short("card 4242 4242 4242 4242, password is hunter2, mail ada@yale.edu " + "x" * 300)
    assert "4242" not in s and "hunter2" not in s and "@" not in s and len(s) <= audit.MAX_TEXT
    print(f"  scrubbing + truncation: {s[:90]}…")


def looping_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # Never finishes: keeps asking for stock, so only the step cap can stop it.
    return ModelResponse(parts=[ToolCallPart("check_stock", {"product_id": "yale-mom-hoodie", "size": "M"})])


def wrong_price_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    called = any(getattr(p, "part_kind", "") == "tool-return" for m in messages for p in m.parts)
    if not called:
        return ModelResponse(parts=[ToolCallPart("get_product_details", {"product_id": "yale-mom-hoodie"})])
    # Always the wrong price, even after the fact check sends it back.
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"message": "The Yale Mom Hoodie is $12.00."})])


async def run_with(fn, deps: ChatDeps) -> tuple[str, dict]:
    with shop_agent.override(model=FunctionModel(fn)):
        reply = await run_chat("How much is the Yale Mom Hoodie in M?", [], deps)
    return reply.message, entries()[-1]


def test_stop_reasons() -> None:
    msg, e = asyncio.run(run_with(looping_model, ChatDeps(user_id=4)))
    assert e["stop_reason"] == "step_limit" and e["customer"] == "user:4", e
    tool_steps = [s for s in e["steps"] if s["type"] == "tool_call"]
    print(f"  step cap: stopped after {len(tool_steps)} tool calls (limit {MAX_MODEL_REQUESTS} model requests) "
          f"-> stop_reason={e['stop_reason']}; reply: {msg[:60]}…")

    msg, e = asyncio.run(run_with(wrong_price_model, ChatDeps()))
    assert e["stop_reason"] == "fact_check_failed" and e["customer"] == "guest", e
    kinds = [s["type"] for s in e["steps"]]
    print(f"  fact check: steps {kinds} -> stop_reason={e['stop_reason']}; reply: {msg[:60]}…")


if __name__ == "__main__":
    test_append_only_and_concurrency()
    test_scrubbing()
    test_stop_reasons()
    print(f"\nAll audit tests passed (temp file: {audit.AUDIT_PATH}).")
