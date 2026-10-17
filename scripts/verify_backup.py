"""Ensaio de recuperação em banco temporário exclusivo; exige credencial administrativa local."""
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.parse import urlparse, urlunparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from escuta.settings import Settings, ROOT
from escuta.repository import Repository


def main():
    settings = Settings.load()
    admin_url = os.environ.get('BACKUP_TEST_ADMIN_URL')
    if not admin_url:
        raise SystemExit('Configure BACKUP_TEST_ADMIN_URL para criar um banco de teste exclusivo.')
    name = 'escuta_restore_' + uuid.uuid4().hex[:12]
    source = urlparse(settings.database_url)
    target = urlunparse(source._replace(path='/' + name))
    binary = os.environ.get('PG_BIN')
    arguments = ['--pg-bin',binary] if binary else []
    backup = ROOT / '.runtime' / (name + '.dump')
    backup.parent.mkdir(parents=True,exist_ok=True)
    env = os.environ.copy(); env['RESTORE_DATABASE_URL'] = target
    created = False
    try:
        with psycopg.connect(admin_url,autocommit=True) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(name),sql.Identifier(source.username)))
            created = True
        target_admin = urlunparse(urlparse(admin_url)._replace(path='/' + name))
        with psycopg.connect(target_admin) as conn:
            conn.execute('CREATE EXTENSION vector')
        tool = str(ROOT / 'scripts' / 'database_backup.py')
        subprocess.run([sys.executable,tool,'backup',str(backup),*arguments],env=env,check=True)
        subprocess.run([sys.executable,tool,'restore',str(backup),*arguments],env=env,check=True)
        repo = Repository(target,settings.dimensions)
        active = repo.active()
        if not active or len(repo.document_ids(active['id'])) != active['metadata']['indexed']:
            raise RuntimeError('Restauração sem coleção ativa completa')
        with repo.connection() as conn:
            row = conn.execute('SELECT embedding <=> embedding AS distance FROM documents LIMIT 1').fetchone()
            if not row or abs(row['distance']) > 1e-5:
                raise RuntimeError('Falha na consulta vetorial restaurada')
        print(f"Restauração verificada: coleção ativa com {active['metadata']['indexed']} documentos e consulta pgvector funcional.")
    finally:
        if created:
            # Somente o nome aleatório criado neste processo, nunca um banco passado pelo usuário.
            with psycopg.connect(admin_url,autocommit=True) as conn:
                conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        backup.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
