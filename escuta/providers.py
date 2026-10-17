"""Portas para IA; timeouts, retries limitados e nenhuma chave em logs."""
import json
import time
import httpx
import numpy as np
from .schemas import Draft, Verification


class ProviderError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or httpx.Client(base_url="https://api.openai.com/v1", timeout=60,
                                             headers={"Authorization": f"Bearer {settings.api_key}"})
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def close(self):
        self.client.close()

    def post(self, path, payload):
        if not self.settings.allow_paid or not self.settings.api_key:
            raise ProviderError("API paga desativada ou chave ausente. Configure .env localmente.")
        for attempt in range(3):
            try:
                response = self.client.post(path, json=payload)
            except httpx.RequestError as exc:
                # Sem retry de timeouts: uma geração pode já ter sido cobrada.
                raise ProviderError("Falha de conexão com o provedor de IA") from exc
            if response.status_code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if response.is_error:
                raise ProviderError(f"Provedor de IA indisponível (HTTP {response.status_code})")
            data = response.json()
            usage = data.get("usage", {})
            self.usage["input_tokens"] += usage.get("input_tokens", usage.get("prompt_tokens", 0))
            self.usage["output_tokens"] += usage.get("output_tokens", 0)
            return data
        raise ProviderError("Limite de tentativas atingido")

    def embed(self, texts, query=False):
        data = self.post("/embeddings", {"model": self.settings.embedding_model, "input": texts,
                                       "dimensions": self.settings.dimensions, "encoding_format": "float"})
        rows = sorted(data.get("data", []), key=lambda x: x["index"])
        if [x["index"] for x in rows] != list(range(len(texts))):
            raise ProviderError("Resposta de embeddings incompleta")
        return normalize([x["embedding"] for x in rows], len(texts), self.settings.dimensions)

    def structured(self, system, user, schema):
        data = self.post("/responses", {
            "model": self.settings.chat_model, "store": False, "max_output_tokens": 1800,
            "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "text": {"format": {"type": "json_schema", "name": schema.__name__.lower(),
                                "strict": True, "schema": schema.model_json_schema()}}})
        if data.get("status") != "completed":
            raise ProviderError("Geração interrompida; nenhuma conclusão será exibida")
        content = [part for item in data.get("output", []) for part in item.get("content", [])]
        if any(p.get("type") == "refusal" for p in content):
            return None
        text = "".join(p.get("text", "") for p in content if p.get("type") == "output_text")
        try:
            return schema.model_validate_json(text)
        except ValueError as exc:
            raise ProviderError("Resposta estruturada inválida") from exc


class OllamaProvider:
    def __init__(self, settings):
        from voice_customer.models import Ollama
        self.model = Ollama(embedding_model=settings.embedding_model, chat_model=settings.chat_model)
        self.settings = settings
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def close(self):
        pass

    def embed(self, texts, query=False):
        try:
            return normalize(self.model.embed(texts, query), len(texts), self.settings.dimensions)
        except Exception as exc:
            raise ProviderError("Falha no modelo local de embeddings") from exc

    def structured(self, system, user, schema):
        try:
            output = self.model.request("/api/chat", {
                "model": self.settings.chat_model, "stream": False, "format": schema.model_json_schema(),
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": 0, "seed": 42, "num_gpu": 0, "num_ctx": 8192, "num_predict": 1000}})
            self.usage["input_tokens"] += output.get("prompt_eval_count", 0)
            self.usage["output_tokens"] += output.get("eval_count", 0)
            return schema.model_validate_json(output["message"]["content"])
        except Exception as exc:
            raise ProviderError("Falha na geração estruturada local") from exc


def normalize(rows, count, dimensions):
    matrix = np.asarray(rows, dtype=np.float32)
    if matrix.shape != (count, dimensions) or not np.isfinite(matrix).all():
        raise ProviderError("Dimensões ou valores dos embeddings inválidos")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ProviderError("Vetor nulo recebido")
    return matrix / norms


def create_provider(settings):
    return OpenAIProvider(settings) if settings.provider == "openai" else OllamaProvider(settings)
