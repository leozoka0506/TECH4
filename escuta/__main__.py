import argparse
import json
import logging
from pathlib import Path
from .settings import Settings, ROOT
from .repository import Repository
from .providers import create_provider
from .ingestion import ingest
from .schemas import Query
from .service import Service


def main():
    parser = argparse.ArgumentParser(description='Escuta: RAG local sobre avaliações Olist')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('migrate', help='Aplica migração idempotente; extensão vector deve existir')
    build = commands.add_parser('ingest', help='Ingestão reiniciável dos quatro CSVs Olist')
    build.add_argument('--raw', type=Path, default=ROOT / 'data' / 'raw')
    build.add_argument('--limit', type=int, default=0, help='0 = corpus completo; >0 = amostra de desenvolvimento')
    build.add_argument('--batch-size', type=int, default=32)
    build.add_argument('--reuse-index', type=Path)
    serve = commands.add_parser('serve')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8501)
    ask = commands.add_parser('ask')
    ask.add_argument('question')
    prune = commands.add_parser('prune-audit')
    prune.add_argument('--days', type=int, default=30)
    args = parser.parse_args()
    settings = Settings.load()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    repo = Repository(settings.database_url, settings.dimensions)
    if args.command == 'migrate':
        repo.migrate()
        print('Migração aplicada.')
    elif args.command == 'serve':
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings), host=args.host, port=args.port, access_log=False)
    elif args.command == 'prune-audit':
        print(json.dumps({'deleted': repo.prune_audit(args.days)}))
    else:
        if args.command == 'ingest' and (args.limit < 0 or not 1 <= args.batch_size <= 256):
            parser.error('limit deve ser >= 0 e batch-size entre 1 e 256')
        provider = create_provider(settings)
        try:
            if args.command == 'ingest':
                collection, manifest = ingest(repo, provider, args.raw, settings, args.limit,
                                              args.batch_size, args.reuse_index)
                print(json.dumps({'collection': collection, **manifest}, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(Service(repo, provider, settings).answer(Query(question=args.question)), ensure_ascii=False, indent=2))
        finally:
            provider.close()


if __name__ == '__main__':
    main()
