#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
container="at208-pg-$$"
baseline_dump="$(mktemp)"
domain_dump="$(mktemp)"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -f "$baseline_dump" "$domain_dump"
}
trap cleanup EXIT

docker run -d --rm --name "$container" --network none \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17-alpine >/dev/null
ready=false
for _ in {1..30}; do
  if docker logs "$container" 2>&1 | grep -q 'PostgreSQL init process complete' && \
    docker exec "$container" psql -X -qAt -U postgres -d postgres \
      -c 'select 1' >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  docker logs "$container"
  exit 1
fi

docker exec "$container" createdb -U postgres at208_test
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_test \
  < "$repo_root/tests/at208/local_auth_fixture.sql"
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_test \
  -c 'grant create on database at208_test to at208_owner'
docker exec "$container" pg_dump -Fc -U postgres -d at208_test > "$baseline_dump"
docker exec "$container" createdb -U postgres at208_guard
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_guard \
  < "$repo_root/tests/at208/local_auth_fixture.sql"
if guard_output="$({
  printf 'set role authenticated;\n'
  cat "$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
} | docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_guard 2>&1)"; then
  echo 'Migration accepted an owner without BYPASSRLS' >&2
  exit 1
fi
[[ "$guard_output" == *'migration owner must have BYPASSRLS'* ]] || {
  echo "Unexpected preflight failure: $guard_output" >&2
  exit 1
}
docker exec "$container" dropdb -U postgres at208_guard
{
  printf 'set role at208_owner;\n'
  cat "$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
} | docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_test
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U postgres -d at208_test \
  < "$repo_root/tests/at208/domain_rls.sql"

docker exec "$container" pg_dump -Fc -U postgres -d at208_test > "$domain_dump"
docker exec "$container" createdb -U postgres at208_restored
docker exec -i "$container" pg_restore -U postgres -d at208_restored < "$domain_dump"
restored="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U postgres -d at208_restored \
  -c "set role authenticated; set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002'; select count(*) from public.projects;")"
[[ "$restored" == 1 ]] || { echo "Restored tenant isolation failed: $restored" >&2; exit 1; }

docker exec "$container" dropdb -U postgres at208_restored
docker exec "$container" createdb -U postgres at208_restored
docker exec -i "$container" pg_restore -U postgres -d at208_restored < "$baseline_dump"
rolled_back="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U postgres -d at208_restored \
  -c "select to_regclass('public.projects') is null and to_regclass('auth.users') is not null;")"
[[ "$rolled_back" == t ]] || { echo "Baseline restore failed: $rolled_back" >&2; exit 1; }
echo 'AT-208 local migration, RLS, backup/restore and baseline rollback passed'
