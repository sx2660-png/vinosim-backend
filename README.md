# VinoSim — local (LangGraph + Gemini + Postgres/pgvector)

A local re-implementation of the VinoSim AI-sommelier backend that was originally built as
6 visual **n8n** workflows. The orchestration is rebuilt with **LangGraph**, the LLM/embeddings/
vision stay on **Google Gemini**, and the vector store is a local **Postgres + pgvector**.

## Flow mapping (n8n → here)

| n8n flow | endpoint | implementation |
|---|---|---|
| Flow 1 · OCR (Vision) | `POST /scan` | Gemini Vision → structured `WineLabel` |
| Flow 2 · AI agent (correction/roleplay) | `POST /agent` | **LangGraph** graph in `app/graph/agent_graph.py` |
| Flow 3 · Get Quiz | `GET /quiz` | random question from Postgres |
| Flow 4 · Submit answer | `POST /quiz/submit` | score + save attempt |
| Flow 5 · Label decoder | `POST /label/decode` | Gemini Vision → generated quiz |
| Flow 6 · Articles | `GET /articles` | list from Postgres |

### Levels and medals (added November 2026)

Two app levels modelled on WSET Level 1 and Level 2 (`app/levels.py`, migrations `sql/005`–`007`):

| endpoint | what it does |
|---|---|
| `GET /quiz?level=1\|2&item_type=` | practice question from one level |
| `GET /progress?user_id=` | both levels, medals earned, whether Level 2 is unlocked (also awards medals) |
| `POST /exam/start`, `POST /exam/submit` | level exam drawn by WSET weights (L1: 30 Q, pass 70%; L2: 50 Q, pass 55%); returns a review |
| `GET/POST /sheets` | four-line tasting sheets; a sheet is complete when the palate line has a structure word and the feeling it refers to |
| `GET /labels/tasks` | Level 2 label questions; correct answers via `/quiz/submit` count toward the medal |
| `GET /bonus`, `POST /bonus/read` | ungraded Level 3–4 reading with small medals |
| `GET /prompts` | ungraded aroma prompts for the sheet |

Level 1 medal = exam passed + 6 complete sheets. Level 2 (unlocks after Level 1) = exam passed + 5 label tasks.

The **Flow-2 graph** mirrors the n8n IF-branch exactly:

```
START → load_history → (IF mode)
                         ├─ correction → retrieve (pgvector) → correction_agent → persist → END
                         └─ roleplay   → roleplay_agent ──────────────────────→ persist → END
```

## Setup

```bash
# 1. Postgres (installed via Homebrew: postgresql@17 + pgvector)
brew services start postgresql@17
bash scripts/setup_db.sh          # creates role/db, applies schema + seed

# 2. Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env              # then paste your GEMINI_API_KEY

# 4. Embed the RAG knowledge base into pgvector
python -m scripts.ingest

# 5. Run the API
uvicorn app.main:app --reload --port 8000
```

Docs UI at http://localhost:8000/docs

## Web client

The main front end is the Lovable app in the separate `vino-wisdom-trainer` repo (TanStack Start). It calls the Railway API by default; run it against a local API with `VITE_API_BASE=http://localhost:8000 bun run dev`. The API contract it uses is in `docs/lovable-handoff.md`.

`web/` is the older phone UI, still served by this API at `/`. It calls:

| screen | call |
|---|---|
| Home, Study | `GET /articles` |
| Quiz | `GET /quiz`, `POST /quiz/submit` |
| Label quiz | `POST /label/decode` |
| Tutor | `POST /agent`, `GET /agent/history`, `POST /scan` |

Article and question photos are `/media/...` files in `web/public/media`. The API serves that folder, and it also serves `web/dist` at `/` when a production build is present.

Two ways to open the UI:

```bash
# Dev: Vite on :5173 proxies /articles, /quiz, /agent, /scan, /label, /health to :8000
cd web && npm install && npm run dev

# One process: build, then open http://127.0.0.1:8000
cd web && npm install && npm run build
uvicorn app.main:app --port 8000
```

A deployed build whose host is not localhost calls `https://vinosim-backend-production.up.railway.app`. Set `VITE_API_BASE` to point a build at a different API. On localhost, a production build calls `http://127.0.0.1:8000` directly. The dev server uses the proxy instead, unless `VITE_API_BASE` is set.

## Try it

```bash
# RAG-grounded correction agent
curl -s localhost:8000/agent -H 'content-type: application/json' -d '{
  "user_id":"u1","mode":"correction","message":"why does my red wine feel so drying?"}' | jq

# roleplay agent (no retrieval)
curl -s localhost:8000/agent -H 'content-type: application/json' -d '{
  "user_id":"u1","mode":"roleplay","message":"this red feels a bit drying on my gums"}' | jq

# quiz
curl -s localhost:8000/quiz | jq
curl -s localhost:8000/quiz/submit -H 'content-type: application/json' -d '{
  "user_id":"u1","question_id":1,"answer":"B"}' | jq

# OCR a label
curl -s localhost:8000/scan -F file=@/path/to/label.jpg | jq
```

## Notes
- Requires a `GEMINI_API_KEY` (chat/embeddings/vision all go to Gemini, matching the original).
- The Gemini client is pinned to API version `v1beta` and `google-genai==2.22.0`. Newer SDK
  releases may call `v1`, which rejects system instructions ("Developer instruction is not
  enabled for api version v1"). Model errors are logged in full; the client gets a short reason.
- On Railway, a changed variable is only staged until you press **Deploy** on the "Apply changes" bar.
- New database: run `scripts/setup_db.sh`. Existing database: back up, then apply `sql/003`–`007`
  in order (each is safe to re-run).
- `wine_docs` embeddings are 768-dim (`gemini-embedding-001`, truncated with
  `output_dimensionality`). Change `EMBED_DIM` **and** the `vector(768)` column
  together if you switch embedding models.
- Retrieval here is single-route pgvector cosine similarity — the same as the n8n PGVector Store
  node. There is no hybrid/BM25/rerank; do not claim those.
