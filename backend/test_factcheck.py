"""Offline test of the reply fact check (no API calls).

A scripted stand-in model (PydanticAI FunctionModel) checks stock, then
deliberately answers with a wrong price and a wrong quantity. The fact check
must reject that draft and force a second answer, which uses the real numbers.

Run from backend/:  python test_factcheck.py
"""

from __future__ import annotations

import asyncio
import json

from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from agent import fact_check_summary, shop_agent
from factcheck import check_reply, collect_facts
from models import ChatDeps

PRODUCT = "ice-hockey-left-chest-hoodie"  # $68.00; XS 20, S 8, M 0, L 0, XL 0, XXL 25


def scripted_model(wrong_first: bool):
    drafts: list[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        out_tool = info.output_tools[0].name
        saw_tool_result = any(
            getattr(p, "tool_name", None) == "check_stock" and p.part_kind == "tool-return"
            for m in messages for p in m.parts
        )
        retried = any(isinstance(p, RetryPromptPart) for m in messages for p in m.parts)
        if not saw_tool_result:
            return ModelResponse(parts=[ToolCallPart("check_stock", {"product_id": PRODUCT, "size": "XXL"})])
        if wrong_first and not retried:
            text = "The Ice Hockey Left Chest Hoodie is $55.00 and we have only 3 left in XXL."
        else:
            text = "The Ice Hockey Left Chest Hoodie is $68.00, and there are 25 in stock in XXL."
        drafts.append(text)
        return ModelResponse(parts=[ToolCallPart(out_tool, {"message": text})])

    return FunctionModel(respond), drafts


async def run(wrong_first: bool):
    model, drafts = scripted_model(wrong_first)
    deps = ChatDeps()
    with shop_agent.override(model=model):
        result = await shop_agent.run("How many XXL of the ice hockey hoodie, and what's the price?", deps=deps)
    return result, deps, drafts


async def main():
    print("== Case 1: model's first draft has a wrong price and quantity ==")
    result, deps, drafts = await run(wrong_first=True)
    for i, d in enumerate(drafts, 1):
        print(f"  draft {i}: {d}")
    retry_notes = [p.content for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
    print(f"  fact check sent back: {retry_notes[0][:330]}...")
    assert "$55.00" in retry_notes[0] and "3 left" in retry_notes[0], "both wrong figures must be flagged"
    print(f"  final reply: {result.output.message}")
    summary = fact_check_summary(deps)
    print(f"  summary: {summary.model_dump()}")
    assert len(drafts) == 2 and "$68.00" in result.output.message and summary.status == "corrected"

    print("\n== Case 2: model gets it right first time ==")
    result, deps, drafts = await run(wrong_first=False)
    summary = fact_check_summary(deps)
    print(f"  final reply: {result.output.message}")
    print(f"  summary: {summary.model_dump()}")
    assert len(drafts) == 1 and summary.status == "verified"

    print("\n== Case 3: unit checks on check_reply ==")
    facts = collect_facts([])
    r = check_reply("It's $68.00 with 25 in stock.", facts)
    print("  no tool called:", r.ok, r.problems)
    assert not r.ok
    r = check_reply("I found 27 hoodies. They're on the page now.", facts)
    print("  no figures:", r.ok, r.prices_checked, r.stock_checked)
    assert r.ok

    print("\nAll fact-check tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
