# AI Shopping Concierge — Embeddable RAG-Powered Chat Widget for E-commerce

A FastAPI backend + embeddable JavaScript widget that gives any e-commerce site an
AI shopping assistant: it answers product questions using hybrid semantic search over
a real catalog, and general store questions (shipping, returns, sizing) from a
separate guarded prompt — grounded, rate-limited, and hardened against prompt injection.

## How it works

1. **Intent classification** — an LLM call (Gemini) first classifies each incoming
   message as `PRODUCT_SEARCH` or `GENERAL_INQUIRY`, so the two conversation types get
   different system prompts and different guardrails.
2. **Hybrid product search** — for product queries, a second LLM call extracts structured
   filters (price range, category) from the natural-language message, which are combined
   with a semantic vector search (Gemini embeddings → Pinecone) as metadata filters. So
   "polo shirts under 3000" does both a semantic match on "polo shirt" *and* a hard
   `price <= 3000` filter — not semantic search alone.
3. **Grounded generation** — the LLM is instructed to answer only from the retrieved
   catalog block, never invent products, prices, or stock — reducing hallucinated listings.
4. **Session memory** — chat history is persisted per session in Redis (with an automatic
   in-memory fallback if Redis is unavailable), capped at a configurable number of turns.
5. **Delivery** — a self-contained `ai-widget.js` file that can be dropped into any site
   as a floating chat button, no framework dependency.

## Security & reliability details

- System prompts explicitly scope the assistant to store topics only, and instruct it to
  treat user text as untrusted input (ignore embedded instructions, never reveal the
  system prompt) — a real prompt-injection defense, not just a "be helpful" prompt.
- Per-session and per-IP rate limiting (`slowapi`) on the chat endpoint.
- CORS is explicitly allow-listed rather than wildcarded.
- Redis failures degrade gracefully to an in-memory session store rather than crashing
  the request.

## Tech stack

FastAPI · Google Gemini (`gemini-2.5-flash`, `gemini-embedding-001`) · Pinecone
(vector DB) · Redis (session store, with in-memory fallback) · slowapi (rate limiting) ·
vanilla JS widget (no frontend framework)

## Status / what's implemented vs. planned

**Implemented and working:**
- Web chat endpoint (`/api/chat`) with intent routing, hybrid catalog search, and
  session-aware responses
- Product catalog embedding/upsert pipeline into Pinecone
- Embeddable widget + demo landing page

**Scaffolded, not yet implemented:**
- `api/routes_whatsapp.py` and `api/routes_instagram.py` exist as placeholders for
  multi-channel support but currently contain no logic — the assistant is web-only today.

## Running locally

```bash
cd Backend
cp .env.example .env   # add GEMINI_API_KEY, PINECONE_API_KEY
docker compose up -d   # starts Redis
pip install -r requirements.txt
python main.py
```

Requires a Pinecone index (`PINECONE_INDEX_NAME`, default `ecommerce-catalog`) seeded
via `database/vector_db.py`'s `upsert_products()`.
