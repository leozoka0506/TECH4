# Operação local e evolução

## Serviços

API: `127.0.0.1:8501`; PostgreSQL: `127.0.0.1:5433`; Ollama: `127.0.0.1:11434`. Não publique essas portas diretamente na internet. A execução padrão usa apenas recursos locais; internet é necessária inicialmente para baixar dependências, base e pesos.

`GET /health/live` verifica o processo. `GET /health/ready` verifica banco e coleção ativa; não executa inferência. `GET /api/status` descreve a coleção. `POST /api/query` recebe `question`, `filters`, `top_k` e `min_similarity`. `GET /metrics` expõe contadores de resultado e histograma de duração. Endpoints de dados e métricas exigem `Authorization: Bearer <APP_TOKEN>` quando o token está configurado.

Exemplo de corpo da consulta:

```json
{"question":"O que os clientes relatam sobre a entrega?","filters":{"max_score":2,"purchase_start":"2018-01-01","purchase_end":"2018-08-31","delivery":"late"},"top_k":6,"min_similarity":0.35}
```

Retornos: 200 com `answered` ou `insufficient`; 401 para token ausente/incorreto; 403 para origem diferente; 422 para entrada inválida; 429 para limite/consulta em andamento; 503 para indisponibilidade. A API não transforma erro de banco ou modelo em ausência de evidência. O ID de requisição aparece nos resultados e logs de consultas. O navegador usa texto literal, sem renderizar HTML de comentários ou do modelo.

## Auditoria e privacidade

`query_audit` contém hash SHA-256 da pergunta, IDs de evidências, coleção, duração, resultado e contagem de tokens, sem armazenar o texto da pergunta. Hash não é anonimização: perguntas previsíveis podem ser reconhecidas por comparação. Os comentários originais e o JSON exportado podem conter informações pessoais que usuários escreveram; trate os arquivos e backups como dados, não como código público.

Logs não incluem credenciais, perguntas ou respostas. Rotacione logs pela infraestrutura e remova auditoria antiga conforme sua política: `python -m escuta prune-audit --days 30`. Esse comando exclui registros de auditoria mais antigos que o período, sem alterar documentos.

## Backup e recuperação

Use `pg_dump`/`pg_restore` da mesma versão principal do servidor ou de uma versão compatível mais recente. Os comandos precisam estar no PATH; na instalação portátil, passe `--pg-bin .runtime/postgres-env/Library/bin`.

```powershell
python scripts/database_backup.py backup data/backups/escuta.dump --pg-bin .runtime/postgres-env/Library/bin
```

O arquivo custom inclui esquema, coleções, vetores, metadados e auditoria. Não substitui backup dos modelos/CSVs se precisar reproduzir os pesos e a fonte exatos. O script recusa sobrescrever arquivos existentes.

Na restauração, comentários de objetos são ignorados (`--no-comments`), para não exigir que o usuário da aplicação seja proprietário da extensão provisionada pelo administrador. Os dados, índices e restrições continuam incluídos.

Restaure em um **novo banco vazio**, com pgvector instalado no servidor. Configure `RESTORE_DATABASE_URL` localmente e execute:

```powershell
python scripts/database_backup.py restore data/backups/escuta.dump --pg-bin .runtime/postgres-env/Library/bin
```

O script recusa usar a mesma URL da aplicação ou um destino com tabelas em `public`. A restauração é transacional e não usa `--clean`. Credenciais são passadas por ambiente, não pela linha de comando. O usuário de restauração precisa poder criar a extensão ou o administrador deve provisioná-la antes. Verifique contagens, coleção ativa e uma consulta de leitura antes de apontar a aplicação ao banco restaurado. Não restaure arquivos de procedência desconhecida.

Proposta de rotina para uma aplicação real: backup diário para outro dispositivo ou armazenamento protegido, retenção definida pelo negócio, criptografia e ensaio periódico de restauração. O projeto fornece a ferramenta; não configura automaticamente agendamento, criptografia, alta disponibilidade ou recuperação ponto a ponto.

## Atualizações e incidentes

- Ingestão interrompida: repita o comando com mesmos dados/modelo/limite; lotes confirmados são preservados.
- Nova base: coloque CSVs atualizados em `data/raw` e ingira; hashes distintos criam nova coleção. Não edite arquivos durante a ingestão.
- Modelo alterado: reconstrua embeddings; não misture modelos, pesos ou dimensões. Conserve os digests para reprodução.
- Resposta sem evidências: confira filtros e corpus; não diminua o limiar indiscriminadamente para forçar resposta.
- 503 de modelo: confira Ollama e `ollama list`; 503 de coleção: execute migração/ingestão e confira as configurações.
- Perda da máquina: restaure o banco e os modelos de cópias externas ou reconstrua a partir dos CSVs. Um backup no mesmo disco não protege contra falha do disco.

## Migração futura para nuvem

O primeiro passo seria PostgreSQL gerenciado com extensão pgvector, conexão privada/TLS e backups automáticos, mudando `DATABASE_URL` e restaurando o banco. A aplicação pode executar em container. Se a IA continuar na máquina do usuário, a aplicação hospedada precisaria alcançar esse serviço por uma conexão privada; apenas mover o banco não torna o sistema independente do computador.

Para múltiplos usuários e disponibilidade contínua, avaliar fila de inferência, autenticação individual/SSO, rate limit compartilhado, segredo gerenciado, proxy HTTPS, observabilidade central, orçamento e dimensionamento. O projeto atual usa um token compartilhado, um processo e limite em memória; não é uma solução multi-tenant ou um cluster de alta disponibilidade. A migração não foi provisionada e não gera custos agora.

Referências: [backup PostgreSQL](https://www.postgresql.org/docs/16/backup-dump.html), [pgvector](https://github.com/pgvector/pgvector), [configuração Ollama](https://docs.ollama.com/faq).
