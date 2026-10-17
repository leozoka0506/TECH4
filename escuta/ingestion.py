"""Junções Olist com cardinalidade controlada: nunca multiplica avaliações por itens."""
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from voice_customer.data import prepare

FILES = ["olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
         "olist_order_items_dataset.csv", "olist_products_dataset.csv"]


def rows(path, required):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError(f"Colunas obrigatórias ausentes em {Path(path).name}")
        yield from reader


def timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def enriched_documents(raw, limit=0):
    raw = Path(raw)
    docs, stats = prepare(raw / FILES[0])
    orders = {}
    for row in rows(raw / FILES[1], ["order_id", "order_status", "order_purchase_timestamp",
                                   "order_delivered_customer_date", "order_estimated_delivery_date"]):
        if row["order_id"] in orders:
            raise ValueError("order_id duplicado no cadastro de pedidos")
        orders[row["order_id"]] = row
    products = {}
    for row in rows(raw / FILES[3], ["product_id", "product_category_name"]):
        if row["product_id"] in products:
            raise ValueError("product_id duplicado no cadastro de produtos")
        products[row["product_id"]] = row["product_category_name"]
    categories, product_ids, items = defaultdict(set), defaultdict(set), defaultdict(int)
    for row in rows(raw / FILES[2], ["order_id", "product_id"]):
        order = row["order_id"]
        items[order] += 1
        product_ids[order].add(row["product_id"])
        category = products.get(row["product_id"])
        if category:
            categories[order].add(category)
    for doc in docs:
        order = orders.get(doc["order_id"], {})
        purchase = timestamp(order.get("order_purchase_timestamp"))
        delivered = timestamp(order.get("order_delivered_customer_date"))
        estimated = timestamp(order.get("order_estimated_delivery_date"))
        # A promessa tem granularidade diária. Entrega no mesmo dia não é atraso.
        delay = (delivered.date() - estimated.date()).days if delivered and estimated else None
        doc.update(purchase_date=purchase.date().isoformat() if purchase else None,
                   delivered_at=delivered.isoformat() if delivered else None,
                   estimated_at=estimated.isoformat() if estimated else None,
                   delay_days=delay, delivery_late=delay > 0 if delay is not None else None,
                   order_status=order.get("order_status") or None,
                   categories=sorted(categories[doc["order_id"]]),
                   product_ids=sorted(product_ids[doc["order_id"]]), item_count=items[doc["order_id"]])
    stats.update(missing_order=sum(d["order_status"] is None for d in docs),
                 unknown_delivery=sum(d["delivery_late"] is None for d in docs),
                 missing_category=sum(not d["categories"] for d in docs))
    hashes = {name: hashlib.sha256((raw / name).read_bytes()).hexdigest() for name in FILES}
    if limit:
        docs = random.Random(42).sample(docs, min(limit, len(docs)))
    manifest = {"source": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
                "files": hashes, "preparation": stats, "indexed": len(docs),
                "selection": "full" if not limit else "random_sample", "seed": 42 if limit else None,
                "schema_version": 2, "limit": limit}
    return docs, manifest


def ingest(repository, provider, raw, settings, limit=0, batch_size=32, reuse_index=None):
    docs, manifest = enriched_documents(raw, limit)
    manifest.update(embedding_model=settings.embedding_model, dimensions=settings.dimensions,
                    provider=settings.provider)
    collection = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:24]
    repository.begin_collection(collection, manifest)
    existing = repository.document_ids(collection)
    reused = {}
    if reuse_index:
        from voice_customer.index import Index
        legacy = Index(reuse_index)
        if legacy.metadata["embedding_model"] != settings.embedding_model or legacy.metadata["dimensions"] != settings.dimensions:
            raise ValueError("Índice anterior usa embedding incompatível")
        reused = {d["text"]: legacy.vectors[i] for i, d in enumerate(legacy.docs)}
    pending = [d for d in docs if d["id"] not in existing]
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        missing = list(dict.fromkeys(d["text"] for d in batch if d["text"] not in reused))
        if missing:
            vectors = provider.embed(missing)
            reused.update(zip(missing, vectors))
        repository.insert_documents(collection, batch, [reused[d["text"]] for d in batch])
        print(json.dumps({"event": "ingestion_progress", "completed": len(existing) + min(start + batch_size, len(pending)),
                          "total": len(docs)}, ensure_ascii=False), flush=True)
    repository.activate(collection, len(docs))
    return collection, manifest
