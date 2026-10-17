"""Índice vetorial exato em NumPy, com publicação atômica de cada versão."""
import hashlib
import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .data import prepare


def build(csv_path, destination, model, limit=0, batch_size=32):
    docs, counts = prepare(csv_path)
    if limit > 0 and limit < len(docs):
        docs = random.Random(42).sample(docs, limit)
    destination = Path(destination)
    version = destination / uuid.uuid4().hex
    version.mkdir(parents=True)
    batches = []
    for start in range(0, len(docs), batch_size):
        batches.append(model.embed([d["text"] for d in docs[start:start + batch_size]]))
        print(f"Embeddings: {min(start + batch_size, len(docs))}/{len(docs)}", flush=True)
    vectors = np.vstack(batches)
    metadata = {"schema": 1, "embedding_model": model.embedding_model, "dimensions": vectors.shape[1],
                "created_at": datetime.now(timezone.utc).isoformat(), "indexed": len(docs),
                "sample_seed": 42 if limit else None, "preparation": counts,
                "source_sha256": hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
                "source": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"}
    (version / "documents.json").write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    (version / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    np.save(version / "vectors.npy", vectors, allow_pickle=False)
    pointer = destination / "CURRENT.tmp"
    pointer.write_text(version.name, encoding="ascii")
    pointer.replace(destination / "CURRENT")
    return metadata


class Index:
    def __init__(self, path):
        path = Path(path)
        try:
            version_name = (path / "CURRENT").read_text(encoding="ascii").strip()
            if len(version_name) != 32 or any(c not in "0123456789abcdef" for c in version_name):
                raise ValueError("Versão inválida.")
            version = path / version_name
            self.docs = json.loads((version / "documents.json").read_text(encoding="utf-8"))
            self.metadata = json.loads((version / "metadata.json").read_text(encoding="utf-8"))
            self.vectors = np.load(version / "vectors.npy", allow_pickle=False)
            if self.vectors.ndim != 2 or self.vectors.shape != (len(self.docs), self.metadata["dimensions"]):
                raise ValueError("Dimensões do índice incompatíveis.")
        except FileNotFoundError as exc:
            raise ValueError("Índice ausente. Execute python -m voice_customer build primeiro.") from exc

    def search(self, question, model, k=6, threshold=0.35, min_score=1, max_score=5, start="", end=""):
        if model.embedding_model != self.metadata["embedding_model"]:
            raise ValueError("Modelo de consulta diferente do índice; reconstrua o índice.")
        eligible = [i for i, d in enumerate(self.docs) if min_score <= d["score"] <= max_score
                    and (not start or bool(d["date"]) and d["date"] >= start)
                    and (not end or bool(d["date"]) and d["date"] <= end)]
        if not eligible:
            return []
        query = model.embed([question], query=True)[0]
        if query.shape != (self.vectors.shape[1],):
            raise ValueError("Dimensão da consulta incompatível com o índice.")
        scores = self.vectors[eligible] @ query
        ranked = sorted(zip(eligible, scores.tolist()), key=lambda item: (-item[1], item[0]))
        hits, texts = [], set()
        for position, score in ranked:
            doc = self.docs[position]
            if score < threshold or doc["text"].casefold() in texts:
                continue
            hits.append({**doc, "similarity": round(score, 5), "citation": f"E{len(hits) + 1}"})
            texts.add(doc["text"].casefold())
            if len(hits) == k:
                break
        return hits
