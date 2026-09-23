#!/usr/bin/env bash
# Create the local `vinosim` role + database and apply schema/seed.
# Assumes a running Postgres 16 (brew) with the current user as superuser.
set -euo pipefail

PG_BIN="/opt/homebrew/opt/postgresql@17/bin"
export PATH="$PG_BIN:$PATH"

DB_USER="vinosim"
DB_PASS="vinosim"
DB_NAME="vinosim"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

echo ">> Creating role + database (idempotent)..."
psql -d postgres -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  END IF;
END \$\$;
SQL

if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  createdb -O "${DB_USER}" "${DB_NAME}"
  echo ">> Created database ${DB_NAME}"
else
  echo ">> Database ${DB_NAME} already exists"
fi

echo ">> Applying schema..."
psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "${HERE}/sql/001_schema.sql"
echo ">> Applying seed (quiz + articles)..."
psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 -f "${HERE}/sql/002_seed.sql"

# make sure the app role owns everything it needs
psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
GRANT ALL ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
GRANT ALL ON SCHEMA public TO ${DB_USER};
SQL

echo ">> DB ready:  postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
echo ">> Next: fill .env, then  python -m scripts.ingest"
