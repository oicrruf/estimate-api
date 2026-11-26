#!/usr/bin/env bash
set -euo pipefail

container="$1"
admin_user="${2:-postgres}"
first_log="$(mktemp)"
trap 'rm -f "$first_log"' EXIT

docker exec "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  -c "set role at208_backend; select private.set_project_member(
    '10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005', 'race-editor',
    '00000000-0000-0000-0000-000000000004', 'editor');" >/dev/null

docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  >"$first_log" 2>&1 <<'SQL' &
begin;
set role at208_backend;
select private.set_project_member(
  '10000000-0000-0000-0000-000000000003',
  '00000000-0000-0000-0000-000000000005', 'race-downgrade',
  '00000000-0000-0000-0000-000000000004', 'viewer');
\! touch /tmp/at208-project-lock-held
select pg_sleep(3);
commit;
SQL
first_pid=$!

ready=false
for _ in {1..30}; do
  if docker exec "$container" test -f /tmp/at208-project-lock-held; then
    ready=true
    break
  fi
  sleep 0.1
done
if [[ "$ready" != true ]]; then
  cat "$first_log"
  echo 'First session did not acquire project lock' >&2
  exit 1
fi

docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test <<'SQL'
set role at208_backend;
do $$ begin
  begin
    perform private.transfer_project_ownership(
      '10000000-0000-0000-0000-000000000003',
      '00000000-0000-0000-0000-000000000005', 'race-transfer',
      '00000000-0000-0000-0000-000000000004');
    raise exception 'concurrent revoked editor became owner';
  exception when check_violation then null; end;
end $$;
SQL
wait "$first_pid"

state="$(docker exec "$container" psql -X -qAt -v ON_ERROR_STOP=1 -U "$admin_user" -d at208_test \
  -c "select owner_user_id = '00000000-0000-0000-0000-000000000005' and
      (select role from public.project_memberships
       where project_id='10000000-0000-0000-0000-000000000003'
         and user_id='00000000-0000-0000-0000-000000000004') = 'viewer'
      from public.projects where id='10000000-0000-0000-0000-000000000003';")"
[[ "$state" == t ]] || { echo "Concurrent transfer state invalid: $state" >&2; exit 1; }
echo 'AT-208 two-session membership/transfer race passed'
