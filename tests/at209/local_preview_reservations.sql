-- Disposable AT-209 preview proof only. Never apply to a hosted database.
create table private.preview_reservations (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references auth.users(id),
  project_id uuid not null references public.projects(id),
  command_key text not null check (length(btrim(command_key)) between 1 and 100),
  created_at timestamptz not null default now(),
  state text not null default 'pending' check (state in ('pending', 'complete', 'failed')),
  response_json jsonb,
  check ((state = 'complete') = (response_json is not null)),
  unique (actor_id, project_id, command_key)
);
create index preview_reservations_recent_idx on private.preview_reservations (created_at);
revoke all on private.preview_reservations from public, anon, authenticated, service_role;
grant usage on schema private to at209_preview_login;
grant select, insert, update (state, response_json) on private.preview_reservations to at209_preview_login;
