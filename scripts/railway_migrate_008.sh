#!/usr/bin/env bash
# Apply sql/008_study_links.sql to the Railway Postgres.
# Copy host, port, user and database from Railway -> Postgres -> Connect (public network).
# The password is read without echo and never written to disk.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
read -rp "Host (e.g. something.proxy.rlwy.net): " PGHOST
read -rp "Port: " PGPORT
read -rp "User [postgres]: " PGUSER; PGUSER=${PGUSER:-postgres}
read -rp "Database [railway]: " PGDATABASE; PGDATABASE=${PGDATABASE:-railway}
read -rsp "Password: " PGPASSWORD; echo
export PGHOST PGPORT PGUSER PGDATABASE PGPASSWORD
psql -v ON_ERROR_STOP=1 -q -f "$HERE/sql/008_study_links.sql"
psql -tAc "SELECT 'linked questions: ' || count(study_slug) || ' of ' || count(*) FROM quiz_questions WHERE app_level IN (1, 2);"
