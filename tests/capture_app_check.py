"""Capture the three app-check screenshots from the live running site.

Needs the backend (uvicorn on :8000) and the front end (Vite on :5173)
running. Drives the installed Google Chrome with Playwright, asks the real
chatbot real questions, waits for the real replies, then saves PNGs to
output/app_check_images/ and the chat transcripts to
output/app_check_images/transcript.json.

Run from the project folder:  .venv/Scripts/python tests/capture_app_check.py
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

SITE = "http://localhost:5173"
OUT = Path(__file__).resolve().parent.parent / "output" / "app_check_images"
VIEWPORT = {"width": 1366, "height": 900}
SCALE = 1.5  # sharper text in the PNGs

REPLY_TIMEOUT_MS = 120_000


def open_chat(page: Page) -> None:
    if page.locator(".chat-panel").count() == 0:
        page.locator(".chat-toggle").click()
    page.locator(".chat-panel").wait_for()


def ask(page: Page, question: str) -> dict:
    """Type a question into the chat widget and wait for Stitch's real reply."""
    open_chat(page)
    before = page.locator(".msg-row.assistant .chat-bubble:not(.typing)").count()
    page.locator(".chat-input textarea").fill(question)
    page.locator(".chat-input button[type=submit]").click()
    page.wait_for_function(
        "n => document.querySelectorAll('.msg-row.assistant .chat-bubble:not(.typing)').length > n"
        " && !document.querySelector('.chat-bubble.typing')",
        arg=before,
        timeout=REPLY_TIMEOUT_MS,
    )
    page.wait_for_timeout(2200)  # let cards finish dealing onto the page / into the chat
    # The panel auto-scrolls to the bottom; scroll back so the question and the
    # start of the answer are at the top of the chat for the screenshot.
    page.evaluate(
        """() => {
            const list = document.querySelector('.chat-messages');
            const q = [...list.querySelectorAll('.msg-row.user')].pop();
            list.scrollTop += q.getBoundingClientRect().top - list.getBoundingClientRect().top - 10;
        }"""
    )
    page.wait_for_timeout(300)
    last = page.locator(".msg-row.assistant .chat-bubble").last
    return {
        "question": question,
        "reply": last.evaluate("b => b.childNodes[0].textContent"),
        "chat_cards": last.locator(".chat-card-name").all_inner_texts(),
        "fact_check": last.locator(".fact-badge").all_inner_texts(),
        "page_url": page.url,
        "page_heading": page.locator("main h1").first.inner_text(),
        "page_cards": page.locator("main .card").count(),
    }


def shoot(page: Page, name: str) -> str:
    path = OUT / name
    page.screenshot(path=str(path))
    return path.name


def fresh_page(browser, path: str) -> Page:
    context = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
    page = context.new_page()
    page.goto(SITE + path)
    page.wait_for_load_state("networkidle")
    return page


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        # 1. Inventory: price + stock for a named item and sizes, one of them sold out.
        page = fresh_page(browser, "/products/ice-hockey-left-chest-hoodie")
        results["inventory"] = ask(
            page, "How much is the Ice Hockey Left Chest Hoodie, and how many do you have in XS and in large?"
        )
        page.evaluate("window.scrollTo(0, 0)")
        results["inventory"]["file"] = shoot(page, "inventory.png")
        page.context.close()

        # 2. Dynamic search results: a category question from the Home page.
        page = fresh_page(browser, "/")
        results["search_results"] = ask(page, "What hoodies do you have?")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        results["search_results"]["file"] = shoot(page, "search_results.png")
        page.context.close()

        # 3. Usability (Problem 9): sold-out size -> in-stock alternatives tool.
        page = fresh_page(browser, "/products/champion-reverse-weave-hoodie-1")
        results["usability"] = ask(page, "Do you have this in XS?")
        page.evaluate("window.scrollTo(0, 0)")
        results["usability"]["file"] = shoot(page, "usability.png")
        page.context.close()

        browser.close()

    (OUT / "transcript.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
