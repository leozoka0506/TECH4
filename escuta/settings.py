from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://escuta@127.0.0.1:5433/escuta"
    provider: str = "ollama"
    api_key: str = ""
    chat_model: str = "qwen2.5:3b"
    embedding_model: str = "embeddinggemma:300m-qat-q4_0"
    dimensions: int = 768
    allow_paid: bool = False
    app_token: str = ""
    environment: str = "development"
    rate_per_minute: int = 20
    verify_claims: bool = True
    response_mode: str = "extractive"

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)
        settings = cls(database_url=os.getenv("DATABASE_URL", cls.database_url),
                       provider=os.getenv("AI_PROVIDER", cls.provider),
                       api_key=os.getenv("OPENAI_API_KEY", ""),
                       chat_model=os.getenv("GENERATION_MODEL", cls.chat_model),
                       embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
                       dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", str(cls.dimensions))),
                       allow_paid=os.getenv("ALLOW_PAID_API", "false").lower() == "true",
                       app_token=os.getenv("APP_TOKEN", ""),
                       environment=os.getenv("APP_ENV", "development"),
                       rate_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")),
                       verify_claims=os.getenv("VERIFY_CLAIMS", "true").lower() == "true",
                       response_mode=os.getenv("RESPONSE_MODE", "extractive"))
        if settings.response_mode not in {"extractive", "summary"}:
            raise ValueError("RESPONSE_MODE deve ser extractive ou summary")
        if settings.provider not in {"openai", "ollama"}:
            raise ValueError("AI_PROVIDER deve ser openai ou ollama")
        if not 1 <= settings.dimensions <= 2000 or not 1 <= settings.rate_per_minute <= 1000:
            raise ValueError("Dimensões ou limite de requisições inválidos")
        if settings.environment == "production" and (len(settings.app_token) < 32 or not settings.database_url.startswith("postgres")):
            raise ValueError("Produção exige PostgreSQL e APP_TOKEN aleatório com pelo menos 32 caracteres")
        return settings
