"""Campus Customs API.

Run from inside backend/:
    uvicorn main:app --reload --port 8000

Serves the product catalogue, live stock and product photos from
data/campus_customs.db, the account routes, and the shop assistant chat.
"""

from __future__ import annotations

import json
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import history
from agent import MODEL_NAME, run_chat
from db import PRODUCTS_DIR, SIZE_RANK, connect_readonly, product_summaries
from safety import scrub_sensitive
from models import (
    ChatDeps,
    ChatHistory,
    ChatReply,
    ChatRequest,
    PageContext,
    ProductDetail,
    ProductSummary,
    SizeStock,
)

log = logging.getLogger("campus_customs")

# --- App ----------------------------------------------------------------------

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/api/products", response_model=list[ProductSummary])
def list_products() -> list[ProductSummary]:
    return product_summaries()


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    summaries = product_summaries([product_id])  # same card data as the list, incl. category
    if not summaries:
        raise HTTPException(status_code=404, detail="Product not found")
    with connect_readonly() as con:
        row = con.execute(
            "SELECT colors, search_tags FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        stock = con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    inventory = sorted(
        (SizeStock(size=s["size"], quantity=s["quantity"], in_stock=s["quantity"] > 0) for s in stock),
        key=lambda s: SIZE_RANK.get(s.size, len(SIZE_RANK)),
    )
    return ProductDetail(
        **summaries[0].model_dump(),
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        inventory=inventory,
    )


def checked_page(page: PageContext) -> tuple[PageContext, str | None]:
    """The browser says which page it's on. Keep a product_id only if it's a
    real catalogue product, and look up its name for the agent."""
    if page.page_type != "product" or not page.product_id:
        return page.model_copy(update={"product_id": None}), None
    with connect_readonly() as con:
        row = con.execute("SELECT name FROM catalogue WHERE product_id = ?", (page.product_id,)).fetchone()
    if row is None:
        return page.model_copy(update={"page_type": "other", "product_id": None}), None
    return page, row["name"]


@app.post("/api/chat", response_model=ChatReply)
async def chat(body: ChatRequest, user_id: int | None = Depends(auth.optional_user_id)) -> ChatReply:
    """One chat turn.

    Who is chatting comes only from the signed session cookie, never from the
    request body. Logged in: the agent gets their name and email, earlier turns
    come from chat_messages (the browser's copy is ignored), and both messages
    are saved. Guest: browser-sent history is used and nothing is saved.
    """
    # Safety: card numbers and passwords never reach the model, the database or the audit trail.
    message, removed = scrub_sensitive(body.message)
    if removed:
        log.warning("removed %s from a chat message before processing", ", ".join(sorted(set(removed))))
    customer = auth.load_customer(user_id) if user_id is not None else None
    if customer is None:
        user_id = None  # stale cookie for a deleted account: treat as a guest
    page, product_name = checked_page(body.page)
    deps = ChatDeps(user_id=user_id, customer=customer, page=page, page_product_name=product_name)
    if user_id is not None:
        turns = history.agent_history(user_id)  # saved turns were scrubbed when stored
    else:
        # A guest's browser sends earlier turns back as typed: scrub those too.
        turns = [t.model_copy(update={"content": scrub_sensitive(t.content)[0]}) for t in body.history]

    try:
        reply = await run_chat(message, turns, deps)
    except Exception:
        # Log the error type only, never the message text or credentials.
        log.exception("chat turn failed")
        raise HTTPException(status_code=502, detail="The shop assistant is unavailable right now.")

    if user_id is not None:
        history.save_turn(user_id, message, reply)
    return reply


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(user_id: int = Depends(auth.current_user_id)) -> ChatHistory:
    """The logged-in customer's own saved chat (401 for guests)."""
    return ChatHistory(messages=history.load_history(user_id))


# Product photos, e.g. /media/products/basic-hoodie-big-yale.jpg. Only the
# products folder is mounted so the database file is never downloadable.
app.mount("/media/products", StaticFiles(directory=PRODUCTS_DIR), name="media")
