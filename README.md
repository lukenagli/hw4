# Campus Customs: Yale apparel shop with an AI shopping assistant

MGT 409 (AI Foundation for Managers), Homework 4. Luke Nagli.

A customer-facing storefront for **Campus Customs**, a Yale apparel shop, with
**Stitch**, a chat assistant built with PydanticAI. Stitch answers from the
shop's live database.

- **Browse** the 102 products, with filters (category, color, size in stock) and sorting.
- **Ask Stitch** about prices and stock ("Is the Ice Hockey hoodie in medium?"). It looks them up with tools, and every price and stock number is fact-checked before it's sent.
- **Search from the chat** ("What hoodies do you have?"). The matching products appear on the page as cards.
- **Sold-out sizes** get in-stock alternatives from the same category at a similar price.
- **Accounts:** log in to have Stitch greet you by name and remember your chat between visits.
- **Safety:** prompt rules backed by code checks, plus an append-only audit trail of every agent run (`output/audit_trail.json`).

Stack: React + Vite + TypeScript (`frontend/`), FastAPI + PydanticAI
(`backend/`), SQLite, and `gpt-5.6-luna` through the Portkey gateway.
Documentation is in `output/`: `harness.md` is the technical guide, plus
`design.md`, `usability.md`, and `app_check.html` with screenshots of the running
app.

---

## 1. What to install

- **Python 3.10 or newer** (tested with 3.14)
- **Node.js 20 or newer** with npm (tested with Node 24)
- **Git**
- A **Portkey API key**: the course key

## 2. Get the code

```bash
git clone https://github.com/lukenagli/hw4.git
cd hw4
```

## 3. Add the data pack (not in git)

The database and product photos are distributed separately. Put them in a
`data/` folder at the top of the project, so that it looks exactly like this:

```text
hw4/
  data/
    campus_customs.db
    products/
      2025-yale-vs-harvard-t-shirt.jpg
      ... (102 .jpg files)
```

If you have the zip (`data.zip`), extracting it at the top of `hw4/` creates
this folder. `data/` is listed in `.gitignore` and must never be committed.

## 4. Create your `.env`

Copy the example file to `.env` **in the top-level `hw4/` folder** (the
same folder as `.env.example`), then put your key in it:

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env   (cmd: copy .env.example .env)
```

Open `.env` and replace the placeholder:

```text
PORTKEY_API_KEY=your-real-portkey-key
```

The other settings in `.env.example` are optional and can stay commented out.

## 5. Start the backend (terminal 1)

From the `hw4/` folder:

```bash
python -m venv .venv
```

Activate it. On Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the requirements, then start the server **from inside `backend/`**:

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Check it: http://127.0.0.1:8000/api/health should show
`{"status":"ok","model":"gpt-5.6-luna"}`.

## 6. Start the front end (terminal 2)

From the `hw4/` folder:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The front end sends `/api` and `/media`
requests on to the backend on port 8000, so start the backend first.

## 7. Test login

| Email | Password |
| --- | --- |
| `test@campuscustoms.yale.edu` | `password` |

You can also create a new account on **Create account**.

## 8. Things to try

Open the chat with the gold **Ask Stitch** button (bottom right). Some things to try:

- Click **"What hoodies do you have?"**. The page fills with hoodie cards.
- Ask **"Show me navy crewnecks under $60"**.
- On the **Champion Reverse Weave Hoodie 1** page, ask **"Do you have this in XS?"**. It's sold out, so Stitch suggests in-stock alternatives.
- Log in as the test user and ask **"What's my name?"**, then log out and back in. Your chat is restored.

## 9. Tests (optional)

Run these from the `hw4/` folder with the virtual environment active.

The first two need no server and make no API calls:

```bash
python tests/test_audit.py
```

```bash
cd backend && python test_factcheck.py
```

These need the backend running. The first sends attack messages to the live chat:

```bash
python tests/safety_attacks.py
```

The second also needs the front end running, `pip install playwright`, and Google Chrome. It recaptures the screenshots in `output/app_check_images/`:

```bash
python tests/capture_app_check.py
```

## Project layout

```text
hw4/
  AI_prompts.md          every prompt used to build this, problem by problem
  requirements.txt       backend Python packages
  .env.example           copy to .env (top level) and add your key
  .gitignore
  README.md
  frontend/              React + Vite + TypeScript app (src/pages, src/components, src/chat, src/auth)
  backend/
    main.py              FastAPI app: products, images, auth, chat routes
    agent.py             PydanticAI agent: model, prompt, tools, loop limits, fact/safety checks, audit hook
    models.py            Pydantic types (tool results, chat contract, agent deps)
    tools.py             the 5 agent tools (read-only SQLite)
    prompts/prompt.md    system prompt (voice, tool rules, safety rules)
    auth.py, db.py, catalogue.py, history.py, factcheck.py, safety.py, audit.py, test_factcheck.py
  tests/                 audit/limit tests, live attack tests, screenshot capture
  output/
    harness.md           technical guide: models, tools, safety, specs
    design.md            visual design rationale
    usability.md         the four usability features and how to see them
    app_check.html       live-site screenshots (open directly in a browser)
    app_check_images/
    audit_trail.json     append-only log of agent runs (no secrets or emails)
    safety_attacks.json  results of tests/safety_attacks.py
  data/                  local only, not in git: campus_customs.db and products/
```

## Notes

- **The database gets written to.** Creating an account or chatting while logged in writes to `data/campus_customs.db`. Products and stock are only ever read.
- **Restart after prompt edits.** `backend/prompts/prompt.md` is loaded at startup. On Windows, `--reload` needs uvicorn running in a normal console window.
- **Optional `.env` settings:** `OPENAI_MODEL` swaps the model, and `FACT_CHECK_DEMO=1` demonstrates the reply fact check (see `output/usability.md`).
