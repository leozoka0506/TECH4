import argparse
import json
from .config import INDEX, RAW
from .index import build, Index
from .models import Ollama, ModelError
from .rag import answer


def main():
    parser = argparse.ArgumentParser(description="Voice of Customer • Olist + RAG local")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="Prepara CSV e cria embeddings persistentes")
    b.add_argument("--csv", default=str(RAW))
    b.add_argument("--index", default=str(INDEX))
    b.add_argument("--limit", type=int, default=0, help="0: corpus completo; >0: amostra aleatória com seed 42")
    s = sub.add_parser("serve", help="Abre servidor web local")
    s.add_argument("--port", type=int, default=8501)
    s.add_argument("--index", default=str(INDEX))
    a = sub.add_parser("ask", help="Pergunta por linha de comando")
    a.add_argument("question")
    a.add_argument("--index", default=str(INDEX))
    a.add_argument("--max-score", type=int, default=5)
    a.add_argument("--threshold", type=float, default=0.35)
    args = parser.parse_args()
    try:
        if args.command == "build":
            if args.limit < 0:
                parser.error("--limit deve ser zero ou positivo")
            print(json.dumps(build(args.csv, args.index, Ollama(), args.limit), indent=2, ensure_ascii=False))
        elif args.command == "serve":
            from .server import serve
            serve(args.port, args.index)
        else:
            index = Index(args.index)
            model = Ollama(embedding_model=index.metadata["embedding_model"])
            print(json.dumps(answer(index, model, args.question, max_score=args.max_score,
                                    threshold=args.threshold), ensure_ascii=False, indent=2))
    except (ValueError, FileNotFoundError, ModelError) as exc:
        parser.exit(1, f"Erro: {exc}\n")


if __name__ == "__main__":
    main()
