"""API de processo único: limita concorrência e mantém dados sensíveis fora de logs."""
import hmac
import json
import logging
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .settings import Settings, ROOT
from .repository import Repository
from .providers import create_provider, ProviderError
from .schemas import Query
from .service import Service


def create_app(settings=None, repository=None, provider=None):
    settings = settings or Settings.load()
    repository = repository or Repository(settings.database_url, settings.dimensions)
    provider = provider or create_provider(settings)
    service = Service(repository, provider, settings)
    gate, rate_lock, requests = threading.Lock(), threading.Lock(), deque()
    registry = CollectorRegistry()
    count = Counter('escuta_queries_total', 'Consultas por resultado', ['status'], registry=registry)
    duration = Histogram('escuta_query_seconds', 'Duração da consulta', buckets=(1, 5, 15, 30, 60, 120, 300), registry=registry)

    @asynccontextmanager
    async def lifespan(app):
        yield
        provider.close()

    app = FastAPI(title='Escuta • Inteligência de avaliações', version='2.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                                 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
                                 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})
        return response

    def authorize(request: Request):
        if settings.app_token:
            expected = f'Bearer {settings.app_token}'
            if not hmac.compare_digest(request.headers.get('authorization', '').encode(), expected.encode()):
                raise HTTPException(401, 'Token de acesso inválido ou ausente')
        origin = request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Origem não autorizada')

    @app.get('/')
    def home():
        return FileResponse(ROOT / 'web' / 'index.html')

    @app.get('/app.js')
    def javascript():
        return FileResponse(ROOT / 'web' / 'app.js', media_type='application/javascript')

    @app.get('/style.css')
    def stylesheet():
        return FileResponse(ROOT / 'web' / 'style.css', media_type='text/css')

    @app.get('/health/live')
    def live():
        return {'status': 'alive'}

    @app.get('/health/ready', dependencies=[Depends(authorize)])
    def ready():
        try:
            if repository.health() and repository.active():
                return {'status': 'ready'}
        except Exception:
            pass
        raise HTTPException(503, 'Banco ou coleção indisponível')

    @app.get('/api/status', dependencies=[Depends(authorize)])
    def status():
        try:
            return {**repository.overview(), 'generation_model': settings.chat_model,
                    'verify_claims': settings.verify_claims}
        except Exception:
            raise HTTPException(503, 'Banco indisponível')

    @app.get('/metrics', dependencies=[Depends(authorize)])
    def metrics():
        return Response(generate_latest(registry), headers={'Content-Type': CONTENT_TYPE_LATEST})

    @app.post('/api/query', dependencies=[Depends(authorize)])
    def query(payload: Query):
        now = time.monotonic()
        with rate_lock:
            while requests and now - requests[0] >= 60:
                requests.popleft()
            if len(requests) >= settings.rate_per_minute:
                raise HTTPException(429, 'Limite global de consultas por minuto atingido', headers={'Retry-After': '60'})
            requests.append(now)
        if not gate.acquire(blocking=False):
            raise HTTPException(429, 'Já existe uma consulta em execução. Aguarde.', headers={'Retry-After': '10'})
        request_id = str(uuid.uuid4())
        tick = time.perf_counter()
        outcome = 'error'
        try:
            result = service.answer(payload, request_id)
            outcome = result['status']
            return result
        except ValueError:
            raise HTTPException(503, 'Coleção ausente ou incompatível; confira a ingestão e os modelos.')
        except ProviderError:
            raise HTTPException(503, 'Modelo indisponível. Confira se o Ollama e os modelos estão disponíveis.')
        except Exception:
            raise HTTPException(503, 'Não foi possível concluir a consulta. Confira a saúde dos serviços.')
        finally:
            elapsed = time.perf_counter() - tick
            gate.release()
            count.labels(outcome).inc()
            duration.observe(elapsed)
            logging.getLogger('escuta').info(json.dumps({'event': 'query', 'request_id': request_id,
                                                       'status': outcome, 'seconds': round(elapsed, 3)}))

    return app
