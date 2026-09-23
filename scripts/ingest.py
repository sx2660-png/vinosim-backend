"""Embed data/wine_docs.jsonl with Gemini and upsert into the pgvector `wine_docs` table.

Run once after the DB is up:  python -m scripts.ingest
"""
from __future__ import annotations

import json
import pathlib
import sys

# allow running as `python scripts/ingest.py` or `python -m scripts.ingest`
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import db, llm  # noqa: E402

DOCS = pathlib.Path(__file__).resolve().parents[1] / "data" / "wine_docs.jsonl"


def main() -> None:
    with db.cursor() as cur:
        cur.execute("TRUNCATE wine_docs RESTART IDENTITY")

    rows = [json.loads(line) for line in DOCS.read_text().splitlines() if line.strip()]
    print(f"Embedding {len(rows)} wine docs with Gemini ({llm.settings.embed_model})...")

    for i, row in enumerate(rows, 1):
        text = f"{row['title']}. {row['content']}"
        emb = llm.embed(text, task_type="RETRIEVAL_DOCUMENT")
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO wine_docs (title, content, metadata, embedding) VALUES (%s, %s, %s, %s)",
                (row["title"], row["content"], json.dumps(row.get("metadata", {})), emb),
            )
        print(f"  [{i}/{len(rows)}] {row['title']}")

    print("Done. wine_docs is populated and indexed.")


if __name__ == "__main__":
    main()
