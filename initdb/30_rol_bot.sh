#!/bin/bash
set -e

echo ">>> Creando rol de solo lectura bot_ro..."

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
	CREATE ROLE bot_ro LOGIN PASSWORD '${BOT_DB_PASSWORD}';
	
	GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO bot_ro;
	GRANT USAGE ON SCHEMA public TO bot_ro;
	GRANT SELECT ON ALL TABLES IN SCHEMA public TO bot_ro;
	ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bot_ro;
	ALTER ROLE bot_ro SET statement_timeout = '25s';
	ALTER ROLE bot_ro SET default_transaction_read_only = on;
EOSQL

echo ">>> Rol bot_ro listo."
