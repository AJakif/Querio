-- Migration 0001: Create chat history schema and tables
-- Idempotent: safe to run multiple times.

CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS chat.sessions (
    id              UUID        PRIMARY KEY,
    account_username TEXT       NULL,
    upload_session_id TEXT      NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat.messages (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      UUID        NOT NULL REFERENCES chat.sessions(id) ON DELETE CASCADE,
    turn_index      INT         NOT NULL,
    question_text   TEXT        NOT NULL,
    answer_json     JSONB       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, turn_index)
);
