#!/bin/bash
set -e

echo ">>> Restaurando nyc_data.backup en la base $POSTGRES_DB..."

pg_restore \
	-U "$POSTGRES_USER" \
	-d "$POSTGRES_DB" \
	--no-owner \
	--no-privileges \
	--verbose \
	/data/nyc_data.backup \
	|| echo ">>> pg_restores terminó con avisos"

echo ">>> Restore completado."
