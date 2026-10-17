"""Preparação auditável: uma avaliação por documento, sem remover negações."""
import csv
import hashlib
import re
from collections import Counter
from datetime import date

REQUIRED = {"review_id", "order_id", "review_score", "review_comment_title",
            "review_comment_message", "review_creation_date"}


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def prepare(path):
    documents, seen, counts = [], set(), Counter()
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("CSV incompatível: faltam colunas oficiais das avaliações Olist.")
        for line, row in enumerate(reader, 2):
            counts["read"] += 1
            title, message = clean(row["review_comment_title"]), clean(row["review_comment_message"])
            text = ". ".join(dict.fromkeys(x for x in (title, message) if x))
            if not text:
                counts["empty"] += 1
                continue
            try:
                score = int(row["review_score"])
                if score not in range(1, 6):
                    raise ValueError()
            except (ValueError, TypeError):
                counts["invalid_score"] += 1
                continue
            review_id, order_id = clean(row["review_id"]), clean(row["order_id"])
            if not review_id or not order_id:
                counts["missing_id"] += 1
                continue
            raw_date = clean(row["review_creation_date"])[:10]
            try:
                created = date.fromisoformat(raw_date).isoformat()
            except ValueError:
                created = ""
                counts["missing_date"] += 1
            # Mesmo texto em pedidos distintos NÃO é duplicata.
            key = (review_id, order_id, score, created, text)
            if key in seen:
                counts["duplicate"] += 1
                continue
            seen.add(key)
            doc_id = hashlib.sha256(repr(key).encode()).hexdigest()[:20]
            documents.append({"id": doc_id, "review_id": review_id, "order_id": order_id,
                              "score": score, "date": created, "text": text, "source_row": line})
    counts["valid"] = len(documents)
    if not documents:
        raise ValueError("Nenhuma avaliação textual válida encontrada.")
    return documents, dict(counts)
