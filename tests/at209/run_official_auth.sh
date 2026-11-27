#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cli="${AT209_SUPABASE_CLI:-/tmp/at209-supabase-cli/node_modules/.bin/supabase}"
[[ -x "$cli" ]] || { echo 'Pinned Supabase CLI 3.4.0 unavailable' >&2; exit 1; }
container_suffix="$$"
net="at209-auth-net-$container_suffix"
db="at209-auth-db-$container_suffix"
auth="at209-auth-service-$container_suffix"
config_file="$(mktemp /tmp/at209-auth-env.XXXXXX)"
signing_file="$(mktemp /tmp/at209-signing.XXXXXX)"
cleanup() {
  docker rm -f "$auth" "$db" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
  rm -f "$config_file" "$signing_file"
}
trap cleanup EXIT
chmod 600 "$config_file" "$signing_file"
password="$(openssl rand -hex 24)"
jwt_secret="$(openssl rand -hex 40)"
( cd /tmp && SUPABASE_HOME="${AT209_SUPABASE_HOME:-/tmp/at209-supabase-home}" \
  SUPABASE_NO_UPDATE_NOTIFIER=1 "$cli" gen signing-key --algorithm ES256 > "$signing_file" )
docker network create "$net" >/dev/null
docker run -d --rm --name "$db" --network "$net" -p 127.0.0.1::5432 \
  -e POSTGRES_PASSWORD="$password" \
  postgres@sha256:f9cf3e1f0066f0eb0c48707d864f0ac5941e9ff454a072077d97a4d278d07d73 >/dev/null
db_ready=false
for _ in {1..60}; do
  if docker logs --tail 120 "$db" 2>&1 | grep -F 'PostgreSQL init process complete' >/dev/null && \
    docker exec "$db" psql -X -qAt -U postgres -d postgres -c 'select 1' >/dev/null 2>&1; then
    db_ready=true
    break
  fi
  sleep 1
done
[[ "$db_ready" == true ]] || { echo 'Disposable PostgreSQL did not start' >&2; exit 1; }
docker exec "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -c 'create schema auth' >/dev/null
python - "$config_file" "$password" "$jwt_secret" "$db" "$signing_file" <<'PY'
from pathlib import Path
import json, sys
path,password,secret,db,keys=sys.argv[1:]
Path(path).write_text('\n'.join([
 'GOTRUE_API_HOST=0.0.0.0', 'GOTRUE_API_PORT=9999',
 'API_EXTERNAL_URL=http://127.0.0.1:55424', 'GOTRUE_SITE_URL=http://127.0.0.1:55424',
 'GOTRUE_DB_DRIVER=postgres',f'GOTRUE_DB_DATABASE_URL=postgres://postgres:{password}@{db}:5432/postgres?search_path=auth',
 'GOTRUE_JWT_AUD=authenticated','GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated',  # pragma: allowlist secret
 'GOTRUE_JWT_EXP=3600',f'GOTRUE_JWT_SECRET={secret}',
 'GOTRUE_JWT_KEYS='+json.dumps([json.loads(Path(keys).read_text())],separators=(',',':')),
 'GOTRUE_JWT_ISSUER=http://127.0.0.1:55424',
 'GOTRUE_EXTERNAL_EMAIL_ENABLED=true','GOTRUE_MAILER_AUTOCONFIRM=true',
 'GOTRUE_DISABLE_SIGNUP=false','GOTRUE_EXTERNAL_PHONE_ENABLED=false',
])+'\n')
Path(path).chmod(0o600)
PY
docker run -d --rm --name "$auth" --network "$net" -p 127.0.0.1:55424:9999 \
  --env-file "$config_file" \
  ghcr.io/supabase/gotrue@sha256:ba8c0c82c574756c835c696df2a2c698020cc408a42034013d3712e34de7964d >/dev/null
ready=false
for _ in {1..80}; do
  if python - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:55424/health',timeout=1)
PY
  then ready=true; break; fi
  [[ "$(docker inspect -f '{{.State.Running}}' "$auth")" == true ]] || break
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Disposable official GoTrue did not start' >&2; exit 1; }
# The AT-208 fixture only supplies roles and auth.uid(); GoTrue owns auth.users.
sed -e '/^create schema auth;$/d' -e '/^create table auth.users (id uuid primary key);$/d' \
  -e '/^create function auth.uid() returns uuid language sql stable as \$\$$/,/^\$\$;$/d' \
  "$repo_root/tests/at208/local_auth_fixture.sql" | \
  docker exec -i "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres
migration="$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
docker exec "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres \
  -c 'grant create on database postgres to at208_owner'
{ printf 'set role at208_owner;\n'; cat "$migration"; } | \
  docker exec -i "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres
docker exec "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres \
  -c "create role at209_read_login login noinherit nobypassrls password '$password'; grant authenticated to at209_read_login with inherit false, set true"
docker exec "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres \
  -c "create role at209_preview_login login noinherit nobypassrls password '$password'; grant authenticated to at209_preview_login with inherit false, set true"
docker exec -i "$db" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres < \
  "$repo_root/tests/at209/local_preview_reservations.sql"
host_port="$(docker port "$db" 5432/tcp | sed -n 's/.*://p')"
[[ -n "$host_port" ]]
ESTIMATE_DB_READ_DSN="postgresql://at209_read_login:$password@127.0.0.1:$host_port/postgres" \
ESTIMATE_DB_TEST_ADMIN_DSN="postgresql://postgres:$password@127.0.0.1:$host_port/postgres" \
ESTIMATE_PREVIEW_LOCAL_DSN="postgresql://at209_preview_login:$password@127.0.0.1:$host_port/postgres" \
ESTIMATE_PREVIEW_LOCAL_ENABLED=1 \
UV_CACHE_DIR=/tmp/at209-uv-cache uv run --no-sync python "$repo_root/tests/at209/verify_official_auth.py"
