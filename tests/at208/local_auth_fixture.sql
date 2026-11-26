-- SOLO PARA POSTGRESQL DESCARTABLE. Nunca aplicar al proyecto Supabase.
-- Simula el contrato auth.uid() para ensayar RLS; NO verifica JWT.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'at208_owner') then
    create role at208_owner nologin bypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'at208_backend') then
    create role at208_backend nologin nobypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'at208_policy_owner') then
    create role at208_policy_owner nologin nobypassrls;
  end if;
end $$;
create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$;
revoke all on schema auth from public;
grant usage on schema auth to authenticated;
grant execute on function auth.uid() to authenticated;
grant usage on schema auth to at208_owner;
grant references on auth.users to at208_owner;
grant execute on function auth.uid() to at208_owner;
grant usage on schema auth to at208_policy_owner;
grant execute on function auth.uid() to at208_policy_owner;
do $$ begin
  if not pg_has_role('at208_owner', 'at208_policy_owner', 'member') then
    grant at208_policy_owner to at208_owner;
  end if;
end $$;
grant create on schema public to at208_owner;
