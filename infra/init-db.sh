#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v app_password="$ESCUTA_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE escuta LOGIN PASSWORD %L', :'app_password') \gexec
GRANT CONNECT ON DATABASE escuta TO escuta;
GRANT USAGE, CREATE ON SCHEMA public TO escuta;
CREATE EXTENSION IF NOT EXISTS vector;
SQL
