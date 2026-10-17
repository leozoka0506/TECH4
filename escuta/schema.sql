-- Migração 001. A extensão deve ser provisionada por um administrador do banco.
CREATE TABLE IF NOT EXISTS schema_version(version integer PRIMARY KEY, dimensions integer NOT NULL);
INSERT INTO schema_version VALUES(1,VECTOR_DIMENSIONS) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS collections(
    id text PRIMARY KEY, metadata jsonb NOT NULL, status text NOT NULL DEFAULT 'building',
    active boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS only_one_active ON collections(active) WHERE active;
CREATE TABLE IF NOT EXISTS documents(
    collection_id text REFERENCES collections(id), id text, body text NOT NULL,
    metadata jsonb NOT NULL, embedding vector(VECTOR_DIMENSIONS) NOT NULL,
    search tsvector GENERATED ALWAYS AS (to_tsvector('portuguese',body)) STORED,
    PRIMARY KEY(collection_id,id)
);
CREATE INDEX IF NOT EXISTS documents_vector ON documents USING hnsw(embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS documents_search ON documents USING gin(search);
CREATE INDEX IF NOT EXISTS documents_metadata ON documents USING gin(metadata);
CREATE INDEX IF NOT EXISTS documents_categories ON documents USING gin((metadata->'categories'));
CREATE INDEX IF NOT EXISTS documents_score ON documents(((metadata->>'score')::integer));
CREATE INDEX IF NOT EXISTS documents_purchase ON documents((metadata->>'purchase_date'));
CREATE TABLE IF NOT EXISTS query_audit(
    request_id uuid PRIMARY KEY, collection_id text, question_hash text NOT NULL,
    outcome text NOT NULL, duration_ms integer NOT NULL, evidence_ids jsonb NOT NULL,
    usage jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_created ON query_audit(created_at);
