-- VinoSim local schema. Mirrors the Postgres/pgvector store used by the n8n pipeline.
CREATE EXTENSION IF NOT EXISTS vector;

-- RAG knowledge base (was: Postgres PGVector Store in the n8n "correction agent" branch)
CREATE TABLE IF NOT EXISTS wine_docs (
    id         BIGSERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding  VECTOR(768)
);
-- Approximate nearest-neighbour index for cosine similarity.
CREATE INDEX IF NOT EXISTS wine_docs_embedding_idx
    ON wine_docs USING hnsw (embedding vector_cosine_ops);

-- Conversation memory (was: "Select Chat History" + "Update Database" nodes)
CREATE TABLE IF NOT EXISTS chat_history (
    id         BIGSERIAL PRIMARY KEY,
    user_id    TEXT NOT NULL,
    mode       TEXT NOT NULL,            -- 'correction' | 'roleplay'
    role       TEXT NOT NULL,            -- 'user' | 'assistant'
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chat_history_user_idx ON chat_history (user_id, created_at);

-- Quiz bank (was: "Get Random Question" / "Get Correct Answer")
CREATE TABLE IF NOT EXISTS quiz_questions (
    id             BIGSERIAL PRIMARY KEY,
    question       TEXT NOT NULL,
    options        JSONB NOT NULL,       -- ["A ...", "B ...", ...]
    correct_answer TEXT NOT NULL,
    explanation    TEXT NOT NULL DEFAULT '',
    category       TEXT NOT NULL DEFAULT 'general'
);

-- Quiz attempts (was: "Save History")
CREATE TABLE IF NOT EXISTS quiz_history (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    question_id BIGINT NOT NULL REFERENCES quiz_questions(id),
    user_answer TEXT NOT NULL,
    is_correct  BOOLEAN NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Study articles (was: "Get Articles")
CREATE TABLE IF NOT EXISTS articles (
    id       BIGSERIAL PRIMARY KEY,
    title    TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    content  TEXT NOT NULL,
    image    TEXT NOT NULL DEFAULT ''
);
