"""Interface local, sem dependência de frameworks e sem serviços pagos."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .config import ROOT, INDEX
from .index import Index
from .models import Ollama, ModelError
from .rag import answer


def serve(port=8501, index_path=INDEX):
    index = Index(index_path)
    model = Ollama(embedding_model=index.metadata["embedding_model"])
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, payload, content_type="application/json; charset=utf-8"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                return self.send(200, (ROOT / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self.send(200, index.metadata)
            return self.send(404, {"error": "Não encontrado."})

        def do_POST(self):
            if self.path != "/api/ask":
                return self.send(404, {"error": "Não encontrado."})
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                return self.send(403, {"error": "Origem não permitida."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length < 12000:
                    return self.send(413, {"error": "Requisição muito grande ou vazia."})
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Envie um objeto JSON.")
                allowed = {k: payload[k] for k in ("k", "threshold", "min_score", "max_score", "start", "end") if k in payload}
                with lock:
                    result = answer(index, model, payload.get("question", ""), **allowed)
                return self.send(200, result)
            except (ValueError, TypeError) as exc:
                return self.send(400, {"error": str(exc)})
            except ModelError as exc:
                return self.send(503, {"error": str(exc)})
            except Exception:
                return self.send(500, {"error": "Falha interna. Confira o índice e reinicie a aplicação."})

    print(f"Voice of Customer disponível em http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
