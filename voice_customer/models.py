"""Cliente HTTP Ollama. Falhas de infraestrutura não viram respostas inventadas."""
import json
import os
import urllib.error
import urllib.request
import numpy as np
from .config import OLLAMA_URL, EMBED_MODEL, CHAT_MODEL

ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["sufficient", "claims"],
    "properties": {
        "sufficient": {"type": "boolean"},
        "claims": {"type": "array", "maxItems": 3, "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "evidence"],
            "properties": {
                "text": {"type": "string"},
                "evidence": {"type": "array", "minItems": 1, "maxItems": 1, "items": {"type": "string"}}
            }}}
    }}


class ModelError(RuntimeError):
    pass


class Ollama:
    def __init__(self, url=OLLAMA_URL, embedding_model=EMBED_MODEL, chat_model=CHAT_MODEL):
        self.url, self.embedding_model, self.chat_model = url, embedding_model, chat_model

    def request(self, route, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.url + route, data=body,
                                         headers={"Content-Type": "application/json"})
        try:
            # Não encaminhar tráfego local por proxies do ambiente.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=300) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelError("Ollama indisponível ou modelo não carregado. Confira o serviço e os modelos instalados.") from exc

    def embed(self, texts, query=False):
        if self.embedding_model.startswith("embeddinggemma"):
            prefix = "task: search result | query: " if query else "title: Avaliação de compra | text: "
            texts = [prefix + text for text in texts]
        result = self.request("/api/embed", {"model": self.embedding_model, "input": texts,
                                            "truncate": False, "keep_alive": "10m",
                                            "options": {"num_gpu": int(os.getenv("EMBED_GPU_LAYERS", "0"))}})
        vectors = np.asarray(result["embeddings"], dtype=np.float32)
        if vectors.ndim != 2 or len(vectors) != len(texts) or not np.isfinite(vectors).all():
            raise ModelError("Embeddings inválidos devolvidos pelo modelo.")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if (norms == 0).any():
            raise ModelError("O modelo devolveu vetor nulo.")
        return vectors / norms

    def chat(self, system, user):
        result = self.request("/api/chat", {
            "model": self.chat_model, "stream": False, "format": ANSWER_SCHEMA,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "seed": 42, "num_ctx": 8192, "num_predict": 800,
                        "num_gpu": int(os.getenv("CHAT_GPU_LAYERS", "0"))}})
        try:
            return json.loads(result["message"]["content"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ModelError("O modelo não devolveu JSON válido. Tente novamente ou use um modelo maior.") from exc
