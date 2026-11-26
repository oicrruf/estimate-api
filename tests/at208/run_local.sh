#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
container="at208-pg-$$"
pg_image="${AT208_PG_IMAGE:-postgres:17-alpine}"
admin_user="${AT208_ADMIN_USER:-postgres}"
baseline_dump="$(mktemp)"
domain_dump="$(mktemp)"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -f "$baseline_dump" "$domain_dump"
}
trap cleanup EXIT

docker run -d --rm --name "$container" --network none \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_PASSWORD=at208-disposable \
  -e POSTGRES_USER="$admin_user" "$pg_image" >/dev/null
ready=false
for _ in {1..300}; do
  if docker logs --tail 200 "$container" 2>&1 | grep -q 'PostgreSQL init process complete' && \
    docker exec "$container" psql -X -qAt -U "$admin_user" -d postgres \
      -c 'select 1' >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  docker logs --tail 150 "$container"
  exit 1
fi

docker exec "$container" createdb -U "$admin_user" at208_test
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  < "$repo_root/tests/at208/local_auth_fixture.sql"
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  -c 'grant create on database at208_test to at208_owner'
docker exec "$container" pg_dump -Fc -U "$admin_user" -d at208_test > "$baseline_dump"
docker exec "$container" createdb -U "$admin_user" at208_guard
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  < "$repo_root/tests/at208/local_auth_fixture.sql"
expect_guard_failure() {
  local expected="$1"
  local active_role="$2"
  local guard_output
  if guard_output="$({
  printf 'set role %s;\n' "$active_role"
  cat "$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
  } | docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard 2>&1)"; then
    echo "Migration accepted forbidden role topology: $expected" >&2
    exit 1
  fi
  [[ "$guard_output" == *"$expected"* ]] || {
    echo "Unexpected preflight failure: $guard_output" >&2
    exit 1
  }
}
expect_guard_failure 'isolated NOLOGIN at208_policy_owner membership required' authenticated
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'alter role at208_policy_owner login'
expect_guard_failure 'isolated NOLOGIN at208_policy_owner membership required' at208_owner
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'alter role at208_policy_owner nologin; grant at208_policy_owner to authenticated'
expect_guard_failure 'helper at208_policy_owner exposed to runtime role authenticated' at208_owner
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'revoke at208_policy_owner from authenticated; grant at208_policy_owner to at208_backend'
expect_guard_failure 'helper at208_policy_owner exposed to runtime role at208_backend' at208_owner
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'revoke at208_policy_owner from at208_backend; create role at208_untrusted login nobypassrls; grant at208_policy_owner to at208_untrusted'
expect_guard_failure 'helper at208_policy_owner exposed to login role at208_untrusted' at208_owner
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'revoke at208_policy_owner from at208_untrusted; drop role at208_untrusted'
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'create role at208_no_set nologin nobypassrls; grant at208_policy_owner to at208_no_set with set false'
expect_guard_failure 'isolated NOLOGIN at208_policy_owner membership required' at208_no_set
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'revoke at208_policy_owner from at208_no_set; drop role at208_no_set; create role at208_platform_admin login superuser'
docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard \
  -c 'grant create on database at208_guard to at208_owner'
{
  printf 'set role at208_owner;\n'
  cat "$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
} | docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_guard
docker exec "$container" dropdb -U "$admin_user" at208_guard
{
  printf 'set role at208_owner;\n'
  cat "$repo_root/supabase/migrations/20261126124001_at_208_postgres_domain.sql"
} | docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  < "$repo_root/tests/at208/domain_rls.sql"
docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  < "$repo_root/tests/at208/trusted_budget.sql"
bash "$repo_root/tests/at208/concurrent_membership.sh" "$container" "$admin_user"

docker exec "$container" pg_dump -Fc -U "$admin_user" -d at208_test > "$domain_dump"
docker exec "$container" createdb -U "$admin_user" at208_restored
docker exec -i "$container" pg_restore -U "$admin_user" -d at208_restored < "$domain_dump"
restored="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_restored \
  -c "set role authenticated; set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002'; select count(*) from public.projects;")"
[[ "$restored" == 1 ]] || { echo "Restored tenant isolation failed: $restored" >&2; exit 1; }
restored_domain="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_restored \
  -c "select
    (select count(*) from public.catalog_items) = 2 and
    (select count(*) from public.project_candidates) = 3 and
    (select count(*) from public.project_selections) = 3 and
    (select count(*) from private.supplier_contacts) = 1 and
    (select count(*) from private.customer_profiles) = 2;")"
[[ "$restored_domain" == t ]] || { echo "Restored domain counts failed: $restored_domain" >&2; exit 1; }

docker exec "$container" dropdb -U "$admin_user" at208_restored
docker exec "$container" createdb -U "$admin_user" at208_restored
docker exec -i "$container" pg_restore -U "$admin_user" -d at208_restored < "$baseline_dump"
rolled_back="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_restored \
  -c "select to_regclass('public.projects') is null and to_regclass('auth.users') is not null;")"
[[ "$rolled_back" == t ]] || { echo "Baseline restore failed: $rolled_back" >&2; exit 1; }
echo 'AT-208 local migration, RLS, backup/restore and baseline rollback passed'
