"""PostgreSQL + pgvector; migração explícita, versões e consultas parametrizadas."""
import json
from contextlib import contextmanager
from pathlib import Path
import numpy as np
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class Repository:
    def __init__(self, url, dimensions=768):
        if not 1 <= dimensions <= 2000:
            raise ValueError("Dimensão inválida")
        self.url, self.dimensions = url, dimensions

    @contextmanager
    def connection(self):
        with psycopg.connect(self.url, connect_timeout=5, row_factory=dict_row) as conn:
            conn.execute("SET statement_timeout = '30s'")
            yield conn

    def migrate(self):
        with self.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(741204)")
            script = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
            conn.execute(script.replace("VECTOR_DIMENSIONS", str(self.dimensions)))
            dimension = conn.execute("SELECT dimensions FROM schema_version WHERE version=1").fetchone()["dimensions"]
            if dimension != self.dimensions:
                raise ValueError("Dimensão mudou: crie outro banco para não misturar espaços vetoriais")

    def health(self):
        with self.connection() as conn:
            return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1

    def begin_collection(self, collection, metadata):
        with self.connection() as conn:
            conn.execute("INSERT INTO collections(id,metadata) VALUES (%s,%s) ON CONFLICT(id) DO NOTHING", (collection, Jsonb(metadata)))

    def document_ids(self, collection):
        with self.connection() as conn:
            return {r["id"] for r in conn.execute("SELECT id FROM documents WHERE collection_id=%s", (collection,))}

    def insert_documents(self, collection, docs, vectors):
        if len(docs) != len(vectors):
            raise ValueError("Número de documentos e vetores diverge")
        with self.connection() as conn:
            for doc, vector in zip(docs, vectors):
                vector = np.asarray(vector, dtype=np.float32)
                if vector.shape != (self.dimensions,) or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
                    raise ValueError("Vetor inválido")
                conn.execute("""INSERT INTO documents(collection_id,id,body,metadata,embedding)
                    VALUES (%s,%s,%s,%s,%s::vector) ON CONFLICT(collection_id,id) DO NOTHING""",
                    (collection, doc["id"], doc["text"], Jsonb(doc), json.dumps(vector.tolist())))

    def activate(self, collection, expected_count):
        with self.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(741205)")
            count = conn.execute("SELECT count(*) AS n FROM documents WHERE collection_id=%s", (collection,)).fetchone()["n"]
            if count != expected_count or count == 0:
                raise ValueError("Coleção incompleta; versão ativa anterior foi preservada")
            conn.execute("UPDATE collections SET active=false WHERE active")
            conn.execute("UPDATE collections SET active=true,status='ready' WHERE id=%s", (collection,))

    def active(self):
        with self.connection() as conn:
            return conn.execute("SELECT id,metadata FROM collections WHERE active AND status='ready'").fetchone()

    @staticmethod
    def filters_sql(filters):
        clauses = ["(metadata->>'score')::int BETWEEN %s AND %s"]
        params = [filters.min_score, filters.max_score]
        for field, start, end in (("purchase_date", filters.purchase_start, filters.purchase_end),
                                  ("date", filters.review_start, filters.review_end)):
            if start:
                clauses.append(f"metadata->>'{field}' >= %s")
                params.append(start.isoformat())
            if end:
                clauses.append(f"NULLIF(metadata->>'{field}','') IS NOT NULL AND metadata->>'{field}' <= %s")
                params.append(end.isoformat())
        if filters.category:
            clauses.append("metadata->'categories' ? %s")
            params.append(filters.category)
        if filters.order_status:
            clauses.append("metadata->>'order_status' = %s")
            params.append(filters.order_status)
        if filters.delivery == "unknown":
            clauses.append("metadata->>'delivery_late' IS NULL")
        elif filters.delivery != "any":
            clauses.append("(metadata->>'delivery_late')::boolean = %s")
            params.append(filters.delivery == "late")
        return " AND ".join(clauses), params

    def retrieve(self, collection, vector, question, filters, candidates=40):
        where, params = self.filters_sql(filters)
        encoded = json.dumps(np.asarray(vector).tolist())
        with self.connection() as conn:
            conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
            conn.execute("SET LOCAL hnsw.ef_search = 100")
            semantic = conn.execute(f"""SELECT id,metadata,1-(embedding <=> %s::vector) AS similarity
                FROM documents WHERE collection_id=%s AND {where}
                ORDER BY embedding <=> %s::vector LIMIT %s""",
                [encoded, collection, *params, encoded, candidates]).fetchall()
            lexical = conn.execute(f"""SELECT id,metadata,1-(embedding <=> %s::vector) AS similarity
                FROM documents WHERE collection_id=%s AND {where}
                AND search @@ plainto_tsquery('portuguese',%s)
                ORDER BY ts_rank_cd(search,plainto_tsquery('portuguese',%s)) DESC,id LIMIT %s""",
                [encoded, collection, *params, question, question, candidates]).fetchall()
        merged = {}
        for group in (semantic, lexical):
            for rank, row in enumerate(group, 1):
                item = merged.setdefault(row["id"], {**row["metadata"], "similarity": float(row["similarity"]), "rrf": 0.0})
                item["rrf"] += 1 / (60 + rank)
        return sorted(merged.values(), key=lambda x: (-x["rrf"], x["id"]))

    def overview(self):
        active = self.active()
        if not active:
            return {"ready": False}
        with self.connection() as conn:
            rows = conn.execute("""SELECT DISTINCT jsonb_array_elements_text(metadata->'categories') AS category
                FROM documents WHERE collection_id=%s ORDER BY category""", (active["id"],)).fetchall()
        return {"ready": True, "collection_id": active["id"], **active["metadata"],
                "categories": [r["category"] for r in rows]}

    def audit(self, request_id, collection, question_hash, outcome, duration, ids, usage):
        with self.connection() as conn:
            conn.execute("""INSERT INTO query_audit(request_id,collection_id,question_hash,outcome,duration_ms,evidence_ids,usage)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""", (request_id, collection, question_hash, outcome, duration, Jsonb(ids), Jsonb(usage)))

    def prune_audit(self, days):
        if days < 1:
            raise ValueError("Retenção mínima de um dia")
        with self.connection() as conn:
            return conn.execute("DELETE FROM query_audit WHERE created_at < now() - (%s * interval '1 day')", (days,)).rowcount
