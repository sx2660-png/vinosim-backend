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

# 5. Run
uvicorn app.main:app --reload --port 8000
```

Docs UI at http://localhost:8000/docs

## Try it

```bash
# RAG-grounded correction agent
curl -s localhost:8000/agent -H 'content-type: application/json' -d '{
  "user_id":"u1","mode":"correction","message":"why does my red wine feel so drying?"}' | jq

# roleplay agent (no retrieval)
curl -s localhost:8000/agent -H 'content-type: application/json' -d '{
  "user_id":"u1","mode":"roleplay","message":"recommend me something fun tonight"}' | jq

# quiz
curl -s localhost:8000/quiz | jq
curl -s localhost:8000/quiz/submit -H 'content-type: application/json' -d '{
  "user_id":"u1","question_id":1,"answer":"B"}' | jq

# OCR a label
curl -s localhost:8000/scan -F file=@/path/to/label.jpg | jq
```

## Notes
- Requires a `GEMINI_API_KEY` (chat/embeddings/vision all go to Gemini, matching the original).
- `wine_docs` embeddings are 768-dim (`text-embedding-004`); change `EMBED_DIM` **and** the
  `vector(768)` column together if you switch embedding models.
- Retrieval here is single-route pgvector cosine similarity — the same as the n8n PGVector Store
  node. There is no hybrid/BM25/rerank; do not claim those.
