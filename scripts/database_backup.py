"""Backup custom do PostgreSQL; restauração somente em banco vazio informado explicitamente."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from escuta.settings import Settings


def pg_environment(url):
    value = urlparse(url)
    if value.scheme not in {'postgres', 'postgresql'} or not value.hostname or not value.path.strip('/'):
        raise ValueError('URL PostgreSQL inválida')
    env = os.environ.copy()
    env.update(PGHOST=value.hostname, PGPORT=str(value.port or 5432),
               PGDATABASE=unquote(value.path.lstrip('/')), PGUSER=unquote(value.username or ''),
               PGPASSWORD=unquote(value.password or ''))
    # Credenciais não aparecem nos argumentos do subprocesso ou logs.
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore'])
    parser.add_argument('file', type=Path)
    parser.add_argument('--pg-bin', type=Path, help='Diretório dos executáveis pg_dump e pg_restore')
    parser.add_argument('--target-env', default='RESTORE_DATABASE_URL', help='Variável com URL do banco vazio de destino')
    args = parser.parse_args()
    settings = Settings.load()
    url = settings.database_url if args.action == 'backup' else os.getenv(args.target_env)
    if not url:
        parser.error('Informe a URL do destino na variável RESTORE_DATABASE_URL')
    env = pg_environment(url)
    if args.action == 'backup':
        if args.file.exists():
            parser.error('Arquivo já existe; escolha outro nome')
        args.file.parent.mkdir(parents=True, exist_ok=True)
        binary = str(args.pg_bin / 'pg_dump') if args.pg_bin else 'pg_dump'
        subprocess.run([binary, '--format=custom', '--no-owner', '--no-acl', '--file', str(args.file)], env=env, check=True)
    else:
        if url == settings.database_url:
            parser.error('Restauração deve usar outro banco, nunca DATABASE_URL')
        if not args.file.is_file():
            parser.error('Backup não encontrado')
        with psycopg.connect(url) as connection:
            tables = connection.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0]
            if tables:
                parser.error('Banco de destino contém tabelas. Restauração recusada.')
        binary = str(args.pg_bin / 'pg_restore') if args.pg_bin else 'pg_restore'
        subprocess.run([binary, '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl', '--no-comments',
                        '--dbname', env['PGDATABASE'], str(args.file)], env=env, check=True)
    print('Operação concluída. Backups contêm dados; mantenha-os fora do Git e protegidos.')


if __name__ == '__main__':
    main()
