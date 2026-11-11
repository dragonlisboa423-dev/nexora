-- SALY global v2: private backend access, no registration or per-user memory.
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS activities (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "activities" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "activities" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE activities FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE activities FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS agent_approvals (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "agent_approvals" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "agent_approvals" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE agent_approvals FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE agent_approvals FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS app_config (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "app_config" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "app_config" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE app_config FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE app_config FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS conversations (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "conversations" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "conversations" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE conversations FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE conversations FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS document_jobs (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "document_jobs" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "document_jobs" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE document_jobs FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE document_jobs FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS documents (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "documents" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "documents" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE documents FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE documents FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS evaluations (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "evaluations" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "evaluations" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE evaluations FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE evaluations FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS lists (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "lists" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "lists" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE lists FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE lists FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS memories (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "memories" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "memories" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE memories FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE memories FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS messages (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "messages" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "messages" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE messages FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE messages FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS owner_access (
	id SERIAL NOT NULL,
	password_hash TEXT NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "owner_access" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "owner_access" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE owner_access FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE owner_access FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS owner_sessions (
	token VARCHAR NOT NULL,
	expires FLOAT NOT NULL,
	PRIMARY KEY (token)
)

;
ALTER TABLE "owner_sessions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "owner_sessions" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE owner_sessions FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE owner_sessions FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS reminders (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "reminders" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "reminders" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE reminders FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE reminders FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS tool_executions (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "tool_executions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "tool_executions" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE tool_executions FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE tool_executions FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS versions (
	id VARCHAR NOT NULL,
	data JSON NOT NULL,
	created VARCHAR NOT NULL,
	updated VARCHAR NOT NULL,
	PRIMARY KEY (id)
)

;
ALTER TABLE "versions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "versions" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE versions FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE versions FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS document_chunks (
	id VARCHAR NOT NULL,
	document_id VARCHAR NOT NULL,
	page INTEGER NOT NULL,
	position INTEGER NOT NULL,
	content TEXT NOT NULL,
	embedding VECTOR(384),
	embedding_version VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)

;
ALTER TABLE "document_chunks" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "document_chunks" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE document_chunks FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE document_chunks FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS document_originals (
	id VARCHAR NOT NULL,
	content BYTEA NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id) REFERENCES documents (id) ON DELETE CASCADE
)

;
ALTER TABLE "document_originals" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "document_originals" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE document_originals FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE document_originals FROM authenticated'; END IF; END $$;

CREATE TABLE IF NOT EXISTS memory_vectors (
	id VARCHAR NOT NULL,
	embedding VECTOR(384) NOT NULL,
	embedding_version VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id) REFERENCES memories (id) ON DELETE CASCADE
)

;
ALTER TABLE "memory_vectors" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE "memory_vectors" FROM PUBLIC;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON TABLE memory_vectors FROM anon'; END IF; IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON TABLE memory_vectors FROM authenticated'; END IF; END $$;
CREATE INDEX IF NOT EXISTS smolin_text_idx ON document_chunks USING gin(to_tsvector('portuguese',content));
CREATE INDEX IF NOT EXISTS smolin_vector_idx ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS memory_vector_idx ON memory_vectors USING hnsw (embedding vector_cosine_ops);
INSERT INTO app_config(id,data) VALUES('schema_version','2'::json) ON CONFLICT(id) DO NOTHING;
COMMIT;
