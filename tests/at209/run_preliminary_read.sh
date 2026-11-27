#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
at208_root="${AT208_ROOT:-$repo_root}"
migration="$at208_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
fixture="$at208_root/tests/at208/local_auth_fixture.sql"
test -s "$migration"
test -s "$fixture"

container="at209-read-$$"
password="$(openssl rand -hex 24)"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --rm --name "$container" -p 127.0.0.1::5432 \
  -e POSTGRES_PASSWORD="$password" -e POSTGRES_HOST_AUTH_METHOD=scram-sha-256 \
  postgres:17-alpine >/dev/null
ready=false
for _ in {1..120}; do
  if docker logs --tail 200 "$container" 2>&1 | grep -F 'PostgreSQL init process complete' >/dev/null && \
    docker exec "$container" psql -X -qAt -U postgres -d postgres \
      -c 'select 1' >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Disposable PostgreSQL not ready' >&2; exit 1; }

docker exec "$container" createdb -U postgres at209_test
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at209_test < "$fixture"
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at209_test \
  -c 'grant create on database at209_test to at208_owner'
{ printf 'set role at208_owner;\n'; cat "$migration"; } | \
  docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at209_test

docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at209_test <<'SQL'
insert into auth.users(id) values
('00000000-0000-0000-0000-000000000001'),
('00000000-0000-0000-0000-000000000002'),
('00000000-0000-0000-0000-000000000003'),
('00000000-0000-0000-0000-000000000004'),
('00000000-0000-0000-0000-000000000005');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.projects(id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000001',
 '00000000-0000-0000-0000-000000000001','Proyecto sintético A');
insert into public.projects(id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000003',
 '00000000-0000-0000-0000-000000000001','Proyecto sintético C');
insert into public.project_memberships(project_id,user_id,role) values
('10000000-0000-0000-0000-000000000001',
 '00000000-0000-0000-0000-000000000003','viewer');
insert into public.project_memberships(project_id,user_id,role) values
('10000000-0000-0000-0000-000000000001',
 '00000000-0000-0000-0000-000000000005','editor');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.projects(id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000002',
 '00000000-0000-0000-0000-000000000002','Proyecto sintético B');
SQL

docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at209_test \
  -c "create role at209_read_login login noinherit nobypassrls password '$password'; grant authenticated to at209_read_login with inherit false, set true"
login_psql() {
  docker exec -e PGPASSWORD="$password" "$container" psql -X -qAt \
    -v ON_ERROR_STOP=1 -h 127.0.0.1 -U at209_read_login -d at209_test "$@"
}
if login_psql -c 'select id from public.projects' >/dev/null 2>&1; then
  echo 'Read LOGIN inherited SELECT before SET ROLE' >&2; exit 1
fi
for suffix in 1 2 3 4 5; do
  actor="$(printf '00000000-0000-0000-0000-%012d' "$suffix")"
  result="$(login_psql -c "begin read only isolation level read committed;
    set local role authenticated;
    set local request.jwt.claim.sub = '$actor';
    select coalesce(string_agg(id::text, ',' order by id), 'none') from public.projects;
    commit;
    select current_user" | paste -sd '|' -)"
  case "$suffix" in
    1) expected='10000000-0000-0000-0000-000000000001,10000000-0000-0000-0000-000000000003|at209_read_login' ;;
    3|5) expected='10000000-0000-0000-0000-000000000001|at209_read_login' ;;
    2) expected='10000000-0000-0000-0000-000000000002|at209_read_login' ;;
    4) expected='none|at209_read_login' ;;
  esac
  [[ "$result" == "$expected" ]] || {
    echo "Read role isolation failed for synthetic user $suffix: $result" >&2; exit 1
  }
done
no_claim="$(login_psql -c "begin read only; set local role authenticated;
  select count(*) from public.projects; commit" )"
[[ "$no_claim" == 0 ]] || { echo "Prior identity leaked: $no_claim" >&2; exit 1; }
echo 'AT-209 preliminary owner/member/outsider RLS and transaction identity passed (JWT not tested)'

host_port="$(docker port "$container" 5432/tcp | sed -n 's/.*://p')"
test -n "$host_port"
ESTIMATE_DB_READ_DSN="postgresql://at209_read_login:$password@127.0.0.1:$host_port/at209_test" \
  ESTIMATE_DB_TEST_ADMIN_DSN="postgresql://postgres:$password@127.0.0.1:$host_port/at209_test" \
  UV_CACHE_DIR=/tmp/at209-uv-cache uv run --no-sync pytest -q tests/at209/test_http_projects.py
