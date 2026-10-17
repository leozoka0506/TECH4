"""Cria configuração local sem imprimir segredos nem sobrescrever arquivo existente."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    raise SystemExit('.env já existe; nenhuma alteração foi feita.')
password, admin, token = (secrets.token_hex(24) for _ in range(3))
text = (root / '.env.example').read_text(encoding='utf-8')
text = text.replace('SUBSTITUA_POR_TOKEN_ALEATORIO_32_CARACTERES', token)
text = text.replace('DB_ADMIN_PASSWORD=SUBSTITUA', f'DB_ADMIN_PASSWORD={admin}')
text = text.replace('SUBSTITUA', password)
with target.open('x', encoding='utf-8') as handle:
    handle.write(text)
print('.env criado. O token de acesso está em APP_TOKEN; mantenha o arquivo privado.')
