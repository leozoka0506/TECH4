"""Inicia PostgreSQL portátil no Windows, sem registrar serviço; instalação prévia necessária."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from escuta.settings import Settings, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT / '.runtime')
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    args = parser.parse_args()
    Settings.load()
    runtime = args.runtime.resolve()
    binary = runtime / 'postgres-env' / 'Library' / 'bin'
    data = runtime / 'postgres-data'
    if not (binary / 'pg_ctl.exe').is_file():
        parser.error('PostgreSQL portátil não encontrado; use Docker ou instale conforme README.')
    env = os.environ.copy()
    env['PATH'] = str(binary) + os.pathsep + env.get('PATH', '')
    def run(name, *params, check=True):
        return subprocess.run([str(binary / (name + '.exe')), *map(str, params)], env=env,
                              check=check, creationflags=subprocess.CREATE_NO_WINDOW)
    if args.action in {'stop','status'}:
        run('pg_ctl','-D',data,args.action)
        return
    for key in ['DB_PASSWORD','DB_ADMIN_PASSWORD']:
        if not os.getenv(key): parser.error('Execute scripts/setup_env.py primeiro.')
    if not (data / 'PG_VERSION').exists():
        # initdb recusa diretório não vazio; nunca sobrescreve um cluster existente.
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf8') as handle:
            handle.write(os.environ['DB_ADMIN_PASSWORD'])
            password_file = Path(handle.name)
        try:
            run('initdb','-D',data,'-U','postgres','--auth=scram-sha-256','--encoding=UTF8',
                '--locale=C','--pwfile',password_file)
        finally:
            password_file.unlink(missing_ok=True)
    if run('pg_ctl','-D',data,'status',check=False).returncode != 0:
        run('pg_ctl','-D',data,'-l',runtime/'postgres.log','-o','-h 127.0.0.1 -p 5433','-w','start')
    with psycopg.connect(host='127.0.0.1',port=5433,user='postgres',password=os.environ['DB_ADMIN_PASSWORD'],dbname='postgres',autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='escuta'").fetchone():
            conn.execute(sql.SQL('CREATE ROLE escuta LOGIN PASSWORD {}').format(sql.Literal(os.environ['DB_PASSWORD'])))
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='escuta'").fetchone():
            conn.execute('CREATE DATABASE escuta OWNER escuta')
    with psycopg.connect(host='127.0.0.1',port=5433,user='postgres',password=os.environ['DB_ADMIN_PASSWORD'],dbname='escuta') as conn:
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
    print('PostgreSQL disponível em 127.0.0.1:5433; banco escuta.')


if __name__ == '__main__':
    main()
