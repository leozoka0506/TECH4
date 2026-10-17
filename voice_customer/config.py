import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "index"
RAW = ROOT / "data" / "raw" / "olist_order_reviews_dataset.csv"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBED_MODEL = os.getenv("EMBED_MODEL", "embeddinggemma:300m-qat-q4_0")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:3b")
