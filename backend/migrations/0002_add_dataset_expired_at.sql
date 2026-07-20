-- Migration 0002: Add dataset_expired_at to track TTL expiry for uploaded session schemas.
-- Idempotent: safe to run multiple times.

ALTER TABLE chat.sessions
    ADD COLUMN IF NOT EXISTS dataset_expired_at TIMESTAMPTZ NULL;
