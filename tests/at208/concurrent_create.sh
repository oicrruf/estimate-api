#!/usr/bin/env bash
set -euo pipefail

container="$1"
admin_user="${2:-postgres}"
first_log="$(mktemp)"
trap 'rm -f "$first_log"' EXIT

docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  >"$first_log" 2>&1 <<'SQL' &
begin;
set role at208_backend;
select private.create_project(
  '10000000-0000-0000-0000-000000000088',
  '00000000-0000-0000-0000-000000000005', 'concurrent-create',
  'Proyecto sintético concurrente');
\! touch /tmp/at208-create-lock-held
select pg_sleep(3);
commit;
SQL
first_pid=$!

ready=false
for _ in {1..30}; do
  if docker exec "$container" test -f /tmp/at208-create-lock-held; then
    ready=true
    break
  fi
  sleep 0.1
done
if [[ "$ready" != true ]]; then
  cat "$first_log" >&2
  echo 'First project creation did not reach the transaction hold' >&2
  exit 1
fi

retry="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  -c "set role at208_backend; select private.create_project(
    '10000000-0000-0000-0000-000000000088',
    '00000000-0000-0000-0000-000000000005', 'concurrent-create',
    'Proyecto sintético concurrente')")"
wait "$first_pid"
[[ "$retry" == '10000000-0000-0000-0000-000000000088' ]] || {
  cat "$first_log" >&2
  echo "Concurrent project retry returned unexpected result: $retry" >&2
  exit 1
}
counts="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  -c "select (select count(*) from public.projects where id='10000000-0000-0000-0000-000000000088'),
             (select count(*) from private.project_command_receipts
              where project_id='10000000-0000-0000-0000-000000000088'
                and command_key='concurrent-create')")"
[[ "$counts" == '1|1' ]] || { echo "Concurrent creation counts invalid: $counts" >&2; exit 1; }
echo 'AT-208 concurrent project creation retry passed'
