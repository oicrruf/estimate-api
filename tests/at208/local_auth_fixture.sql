-- SOLO PARA POSTGRESQL DESCARTABLE. Nunca aplicar al proyecto Supabase.
-- Simula el contrato auth.uid() para ensayar RLS; NO verifica JWT.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
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
