"""
Apply all pending database migrations manually.

Fixes: ORM model has columns not in DB → all SELECT queries fail silently.
Root cause: Alembic version stuck at 20260313a002 (missing migration file).

Migrations applied:
- 20260315a001: agent_query_traces + agent_tool_call_logs
- 20260316a001: agent_learnings
- 20260315a002: document_chunks
- 20260315a003: BM25 tsvector + trigger

Usage: python scripts/fixes/apply_pending_migrations.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

import asyncpg


async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents")
    dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn=dsn)
    print(f"Connected to database")

    ver = await conn.fetchval("SELECT version_num FROM alembic_version")
    print(f"Current alembic version: {ver}")

    # === 20260315a001: agent_query_traces + agent_tool_call_logs ===
    print("\n--- 20260315a001: agent trace tables ---")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_query_traces (
            id SERIAL PRIMARY KEY,
            query_id VARCHAR(64) NOT NULL UNIQUE,
            question TEXT NOT NULL,
            context VARCHAR(20),
            route_type VARCHAR(20) NOT NULL DEFAULT 'llm',
            plan_tool_count INTEGER DEFAULT 0,
            hint_count INTEGER DEFAULT 0,
            iterations INTEGER DEFAULT 0,
            total_results INTEGER DEFAULT 0,
            correction_triggered BOOLEAN DEFAULT false,
            react_triggered BOOLEAN DEFAULT false,
            citation_count INTEGER DEFAULT 0,
            citation_verified INTEGER DEFAULT 0,
            answer_length INTEGER DEFAULT 0,
            total_ms INTEGER DEFAULT 0,
            model_used VARCHAR(50),
            feedback_score SMALLINT,
            feedback_text VARCHAR(500),
            feedback_at TIMESTAMPTZ,
            answer_preview VARCHAR(500),
            tools_used JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_query_traces_query_id ON agent_query_traces (query_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_trace_created ON agent_query_traces (created_at)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_trace_context ON agent_query_traces (context, created_at)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_trace_route ON agent_query_traces (route_type, created_at)")
    print("  agent_query_traces: OK")

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_tool_call_logs (
            id SERIAL PRIMARY KEY,
            trace_id INTEGER NOT NULL REFERENCES agent_query_traces(id) ON DELETE CASCADE,
            tool_name VARCHAR(50) NOT NULL,
            params JSONB,
            success BOOLEAN NOT NULL DEFAULT true,
            result_count INTEGER DEFAULT 0,
            duration_ms INTEGER DEFAULT 0,
            error_message VARCHAR(500),
            call_order SMALLINT DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_tool_call_logs_trace_id ON agent_tool_call_logs (trace_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_tool_log_name ON agent_tool_call_logs (tool_name, created_at)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_tool_log_success ON agent_tool_call_logs (tool_name, success)")
    print("  agent_tool_call_logs: OK")

    # === 20260316a001: agent_learnings ===
    print("\n--- 20260316a001: agent_learnings ---")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_learnings (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            learning_type VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR(32) NOT NULL,
            source_question TEXT,
            confidence FLOAT DEFAULT 1.0,
            hit_count INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_learning_type ON agent_learnings (learning_type)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_learning_session ON agent_learnings (session_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_learning_active_type ON agent_learnings (is_active, learning_type)")
    print("  agent_learnings: OK")

    # === 20260315a002: document_chunks ===
    print("\n--- 20260315a002: document_chunks ---")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            start_char INTEGER,
            end_char INTEGER,
            token_count INTEGER,
            created_at TIMESTAMP DEFAULT now()
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_document_id ON document_chunks (document_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_doc_idx ON document_chunks (document_id, chunk_index)")

    # pgvector conditional
    await conn.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                BEGIN
                    ALTER TABLE document_chunks ADD COLUMN embedding vector(768);
                EXCEPTION WHEN duplicate_column THEN
                    NULL;
                END;
            END IF;
        END $$;
    """)
    print("  document_chunks: OK")

    # === 20260315a003: BM25 tsvector ===
    print("\n--- 20260315a003: BM25 tsvector ---")
    has_sv = await conn.fetchval("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'search_vector'
    """)
    if not has_sv:
        await conn.execute("ALTER TABLE documents ADD COLUMN search_vector tsvector")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_documents_search_vector ON documents USING GIN (search_vector)")

        r = await conn.execute("""
            UPDATE documents SET search_vector =
                setweight(to_tsvector('simple', COALESCE(subject, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(sender, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(receiver, '')), 'B') ||
                setweight(to_tsvector('simple', COALESCE(doc_number, '')), 'A') ||
                setweight(to_tsvector('simple', COALESCE(ck_note, '')), 'C')
        """)
        print(f"  Updated search_vector: {r}")

        await conn.execute("""
            CREATE OR REPLACE FUNCTION documents_search_vector_trigger()
            RETURNS trigger AS $func$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('simple', COALESCE(NEW.subject, '')), 'A') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.sender, '')), 'B') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.receiver, '')), 'B') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.doc_number, '')), 'A') ||
                    setweight(to_tsvector('simple', COALESCE(NEW.ck_note, '')), 'C');
                RETURN NEW;
            END
            $func$ LANGUAGE plpgsql
        """)
        await conn.execute("""
            DROP TRIGGER IF EXISTS tsvector_update ON documents;
            CREATE TRIGGER tsvector_update
                BEFORE INSERT OR UPDATE ON documents
                FOR EACH ROW EXECUTE FUNCTION documents_search_vector_trigger()
        """)
        print("  BM25 trigger: OK")
    else:
        print("  BM25 tsvector: already exists")

    # === Stamp alembic ===
    await conn.execute("UPDATE alembic_version SET version_num = '20260315a003'")
    ver = await conn.fetchval("SELECT version_num FROM alembic_version")
    print(f"\nAlembic stamped to: {ver}")

    # === Verify ===
    print("\n--- Verification ---")
    for tbl in ["agent_query_traces", "agent_tool_call_logs", "document_chunks", "agent_learnings"]:
        exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{tbl}')")
        print(f"  {tbl}: {'OK' if exists else 'MISSING!'}")

    ner = await conn.fetchval("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'ner_pending'
    """)
    print(f"  documents.ner_pending: {'OK' if ner else 'MISSING!'}")

    sv = await conn.fetchval("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'search_vector'
    """)
    print(f"  documents.search_vector: {'OK' if sv else 'MISSING!'}")

    await conn.close()
    print("\n=== ALL MIGRATIONS APPLIED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(main())
