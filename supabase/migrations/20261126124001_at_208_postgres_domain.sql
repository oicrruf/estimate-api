-- AT-208: proyecto universal, historia comercial e aislamiento por proyecto.
-- Requiere roles Supabase anon/authenticated y auth.uid()/auth.users.
begin;

-- Roles NOLOGIN y NOBYPASS aprovisionados por un administrador fuera de esta
-- migración. Fallar antes de crear objetos si faltan o el migrador no puede
-- transferirles la propiedad de funciones. Nada aquí modifica roles alojados.
do $$
declare
  helper name;
  exposed_role name;
begin
  if not exists (select 1 from pg_roles
                 where rolname = 'at208_backend' and not rolbypassrls and not rolsuper) then
    raise exception 'dedicated at208_backend role without BYPASSRLS required'
      using errcode = '42501';
  end if;
  if not exists (select 1 from pg_roles
                 where rolname = 'at208_policy_owner' and not rolcanlogin
                   and not rolbypassrls and not rolsuper)
     or not pg_has_role(current_user, 'at208_policy_owner', 'member') then
    raise exception 'isolated NOLOGIN at208_policy_owner membership required'
      using errcode = '42501';
  end if;
  if not exists (select 1 from pg_roles
                 where rolname = 'at208_mutation_owner' and not rolcanlogin
                   and not rolbypassrls and not rolsuper)
     or not pg_has_role(current_user, 'at208_mutation_owner', 'member') then
    raise exception 'isolated NOLOGIN at208_mutation_owner membership required'
      using errcode = '42501';
  end if;
  if not exists (select 1 from pg_roles
                 where rolname = 'at208_audit_owner' and not rolcanlogin
                   and not rolbypassrls and not rolsuper)
     or not pg_has_role(current_user, 'at208_audit_owner', 'member') then
    raise exception 'isolated NOLOGIN at208_audit_owner membership required'
      using errcode = '42501';
  end if;
  for helper in select unnest(array[
    'at208_policy_owner', 'at208_mutation_owner', 'at208_audit_owner']::name[])
  loop
    -- El rol conectado que ejecuta la migración es el único LOGIN autorizado
    -- a asumir estos propietarios. Las sesiones normales no deben heredarlos.
    select r.rolname into exposed_role from pg_roles r
    where r.rolcanlogin and r.rolname <> session_user
      and pg_has_role(r.rolname, helper, 'member') limit 1;
    if found then
      raise exception 'helper % exposed to login role %', helper, exposed_role
        using errcode = '42501';
    end if;
    select r.rolname into exposed_role from pg_roles r
    where r.rolname in ('anon', 'authenticated', 'service_role',
                        'at208_backend', 'authenticator')
      and pg_has_role(r.rolname, helper, 'member') limit 1;
    if found then
      raise exception 'helper % exposed to runtime role %', helper, exposed_role
        using errcode = '42501';
    end if;
  end loop;
end $$;

create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;
grant usage on schema private to at208_backend;
grant usage, create on schema private to at208_policy_owner;
grant usage, create on schema private to at208_mutation_owner, at208_audit_owner;

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete restrict,
  name text not null check (length(btrim(name)) between 1 and 200),
  revision bigint not null default 1 check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index projects_owner_idx on public.projects (owner_user_id, id);

create table public.project_memberships (
  project_id uuid not null references public.projects(id) on delete restrict,
  user_id uuid not null references auth.users(id) on delete restrict,
  role text not null check (role in ('editor', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (project_id, user_id)
);
create index memberships_user_idx on public.project_memberships (user_id, project_id, role);

create table public.catalog_items (
  id uuid primary key default gen_random_uuid(),
  namespace text not null check (length(btrim(namespace)) > 0),
  version text not null check (length(btrim(version)) > 0),
  brand text not null check (length(btrim(brand)) > 0),
  model text not null check (length(btrim(model)) > 0),
  sku text not null check (length(btrim(sku)) > 0),
  label text not null check (length(btrim(label)) > 0),
  facts jsonb not null default '{}'::jsonb check (jsonb_typeof(facts) = 'object'),
  created_at timestamptz not null default now(),
  unique (namespace, version, sku)
);
create unique index catalog_product_identity_idx on public.catalog_items
  (lower(btrim(brand)), lower(btrim(model)), lower(btrim(sku)));

create table public.countries (
  code char(2) primary key check (code ~ '^[A-Z]{2}$'),
  name text not null check (length(btrim(name)) > 0)
);
create table public.suppliers (
  id uuid primary key default gen_random_uuid(),
  country_code char(2) not null references public.countries(code) on delete restrict,
  display_name text not null check (length(btrim(display_name)) > 0),
  registry_ref text not null check (length(btrim(registry_ref)) > 0),
  unique (country_code, registry_ref)
);
create index suppliers_name_idx on public.suppliers (display_name);
create table public.supplier_branches (
  id uuid primary key default gen_random_uuid(),
  supplier_id uuid not null references public.suppliers(id) on delete restrict,
  country_code char(2) not null references public.countries(code) on delete restrict,
  branch_ref text not null check (length(btrim(branch_ref)) > 0),
  label text not null check (length(btrim(label)) > 0),
  unique (supplier_id, id),
  unique (supplier_id, branch_ref)
);
create index branches_country_idx on public.supplier_branches (country_code, supplier_id);
create table private.supplier_contacts (
  id uuid primary key default gen_random_uuid(),
  branch_id uuid not null references public.supplier_branches(id) on delete restrict,
  name text not null check (length(btrim(name)) > 0),
  email text,
  phone text
);
create index supplier_contacts_branch_idx on private.supplier_contacts (branch_id);

create table public.research_sources (
  id uuid primary key default gen_random_uuid(),
  source_ref text not null unique check (length(btrim(source_ref)) > 0),
  title text not null check (length(btrim(title)) > 0),
  observed_at timestamptz not null
);
create table public.product_equivalences (
  left_item_id uuid not null references public.catalog_items(id) on delete restrict,
  right_item_id uuid not null references public.catalog_items(id) on delete restrict,
  source_id uuid not null references public.research_sources(id) on delete restrict,
  relation text not null check (relation in ('verified_equivalent', 'compatible_alternative')),
  primary key (left_item_id, right_item_id, source_id),
  check (left_item_id < right_item_id)
);
create table public.product_specs (
  catalog_item_id uuid not null references public.catalog_items(id) on delete restrict,
  spec_key text not null check (length(btrim(spec_key)) > 0),
  value_text text not null check (length(btrim(value_text)) > 0),
  source_id uuid not null references public.research_sources(id) on delete restrict,
  primary key (catalog_item_id, spec_key, source_id)
);
create index product_specs_source_idx on public.product_specs (source_id);
create table public.product_warranties (
  catalog_item_id uuid not null references public.catalog_items(id) on delete restrict,
  source_id uuid not null references public.research_sources(id) on delete restrict,
  months integer not null check (months >= 0),
  terms_ref text not null check (length(btrim(terms_ref)) > 0),
  primary key (catalog_item_id, source_id)
);
create table public.knowledge_package_versions (
  namespace text not null check (length(btrim(namespace)) > 0),
  version text not null check (length(btrim(version)) > 0),
  source_id uuid not null references public.research_sources(id) on delete restrict,
  facts jsonb not null check (jsonb_typeof(facts) = 'object'),
  primary key (namespace, version)
);
create table public.service_definitions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (length(btrim(code)) > 0),
  label text not null check (length(btrim(label)) > 0)
);

create table public.project_customers (
  project_id uuid not null references public.projects(id) on delete restrict,
  id uuid not null default gen_random_uuid(),
  customer_ref text not null check (length(btrim(customer_ref)) > 0),
  country_code char(2) not null references public.countries(code) on delete restrict,
  primary key (project_id, id),
  unique (project_id, customer_ref)
);
create table private.customer_profiles (
  project_id uuid not null,
  customer_id uuid not null,
  legal_name text not null check (length(btrim(legal_name)) > 0),
  contact_email text,
  primary key (project_id, customer_id),
  foreign key (project_id, customer_id)
    references public.project_customers(project_id, id) on delete restrict
);

create table public.project_entities (
  project_id uuid not null references public.projects(id) on delete restrict,
  entity_id text not null check (length(btrim(entity_id)) > 0),
  kind text not null check (kind in (
    'ProjectGoal', 'Requirement', 'Capability', 'Resource', 'Task', 'Deliverable',
    'Constraint', 'SiteCondition', 'Evidence', 'Dependency', 'BOMLine', 'Rule', 'Approval'
  )),
  label text not null check (length(btrim(label)) > 0),
  origin_kind text not null check (origin_kind in ('user', 'document', 'agent', 'system')),
  origin_ref text not null check (length(btrim(origin_ref)) > 0),
  scope_kind text not null check (scope_kind in ('project', 'site', 'area', 'workstream')),
  scope_id text not null check (length(btrim(scope_id)) > 0),
  revision bigint not null check (revision > 0),
  knowledge_state text not null check (knowledge_state in ('known', 'assumed', 'unknown', 'conflicted')),
  details jsonb not null default '{}'::jsonb check (jsonb_typeof(details) = 'object'),
  created_at timestamptz not null default now(),
  primary key (project_id, entity_id)
);
create index project_entities_kind_idx on public.project_entities (project_id, kind);

create table public.project_relations (
  project_id uuid not null references public.projects(id) on delete restrict,
  source_entity_id text not null,
  predicate text not null check (length(btrim(predicate)) > 0),
  target_entity_id text not null,
  created_at timestamptz not null default now(),
  primary key (project_id, source_entity_id, predicate, target_entity_id),
  foreign key (project_id, source_entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict,
  foreign key (project_id, target_entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index project_relations_target_idx on public.project_relations (project_id, target_entity_id);

create table public.project_packages (
  project_id uuid not null references public.projects(id) on delete restrict,
  package_id text not null check (length(btrim(package_id)) > 0),
  namespace text not null check (length(btrim(namespace)) > 0),
  version text not null check (length(btrim(version)) > 0),
  subject_entity_id text not null,
  facts jsonb not null check (jsonb_typeof(facts) = 'object'),
  created_at timestamptz not null default now(),
  primary key (project_id, package_id),
  foreign key (namespace, version)
    references public.knowledge_package_versions(namespace, version) on delete restrict,
  foreign key (project_id, subject_entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index project_packages_subject_idx on public.project_packages (project_id, subject_entity_id);

create table public.project_candidates (
  project_id uuid not null,
  requirement_entity_id text not null,
  catalog_item_id uuid not null references public.catalog_items(id) on delete restrict,
  status text not null check (status in ('proposed', 'rejected', 'selected')),
  evidence_ref text not null,
  created_at timestamptz not null default now(),
  primary key (project_id, requirement_entity_id, catalog_item_id),
  unique (project_id, requirement_entity_id, catalog_item_id, status),
  foreign key (project_id, requirement_entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict,
  foreign key (project_id, evidence_ref)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index candidates_product_idx on public.project_candidates (catalog_item_id, project_id);
create table public.project_evaluations (
  project_id uuid not null,
  id uuid not null default gen_random_uuid(),
  evaluation_seq bigint generated always as identity unique,
  requirement_entity_id text not null,
  catalog_item_id uuid not null,
  evidence_ref text not null,
  outcome text not null check (outcome in ('accepted', 'rejected', 'needs_review')),
  rationale text not null check (length(btrim(rationale)) > 0),
  created_at timestamptz not null default now(),
  primary key (project_id, id),
  unique (project_id, id, requirement_entity_id, catalog_item_id, outcome),
  foreign key (project_id, requirement_entity_id, catalog_item_id)
    references public.project_candidates(project_id, requirement_entity_id, catalog_item_id)
    on delete restrict,
  foreign key (project_id, evidence_ref)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index evaluations_candidate_idx on public.project_evaluations
  (project_id, requirement_entity_id, catalog_item_id, evaluation_seq desc);
create table public.project_selections (
  project_id uuid not null,
  id uuid not null default gen_random_uuid(),
  requirement_entity_id text not null,
  catalog_item_id uuid not null,
  evaluation_id uuid not null,
  evaluation_outcome text not null default 'accepted' check (evaluation_outcome = 'accepted'),
  status text not null default 'active' check (status in ('active', 'superseded')),
  selected_at timestamptz not null default now(),
  superseded_at timestamptz,
  primary key (project_id, id),
  check ((status = 'active' and superseded_at is null) or
         (status = 'superseded' and superseded_at is not null)),
  foreign key (project_id, requirement_entity_id, catalog_item_id)
    references public.project_candidates(project_id, requirement_entity_id, catalog_item_id)
    on delete restrict,
  foreign key (project_id, evaluation_id, requirement_entity_id, catalog_item_id,
               evaluation_outcome)
    references public.project_evaluations(project_id, id, requirement_entity_id,
                                          catalog_item_id, outcome) on delete restrict
);
create unique index project_selections_one_active_idx on public.project_selections
  (project_id, requirement_entity_id) where status = 'active';

create table public.project_offers (
  project_id uuid not null references public.projects(id) on delete restrict,
  id uuid not null default gen_random_uuid(),
  catalog_item_id uuid not null references public.catalog_items(id) on delete restrict,
  supplier_id uuid not null references public.suppliers(id) on delete restrict,
  supplier_branch_id uuid,
  source_id uuid not null references public.research_sources(id) on delete restrict,
  supplier_ref text not null check (length(btrim(supplier_ref)) > 0),
  observed_at timestamptz not null default now(),
  valid_from date not null,
  valid_until date,
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  unit_price numeric(18,4) not null check (
    unit_price >= 0 and unit_price <> all (
      array['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])),
  evidence_ref text not null check (length(btrim(evidence_ref)) > 0),
  evidence_revision bigint not null check (evidence_revision > 0),
  evidence_snapshot jsonb not null check (jsonb_typeof(evidence_snapshot) = 'object'),
  observation_status text not null default 'observed'
    check (observation_status in ('observed', 'expired', 'retracted')),
  primary key (project_id, id),
  check (valid_until is null or valid_until >= valid_from),
  foreign key (supplier_id, supplier_branch_id)
    references public.supplier_branches(supplier_id, id) on delete restrict,
  foreign key (project_id, evidence_ref)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index project_offers_history_idx on public.project_offers (project_id, catalog_item_id, observed_at desc);
create index project_offers_supplier_idx on public.project_offers (supplier_id, observed_at desc);

create table public.project_service_rates (
  project_id uuid not null references public.projects(id) on delete restrict,
  id uuid not null default gen_random_uuid(),
  service_id uuid not null references public.service_definitions(id) on delete restrict,
  source_id uuid not null references public.research_sources(id) on delete restrict,
  evidence_ref text not null,
  evidence_revision bigint not null check (evidence_revision > 0),
  evidence_snapshot jsonb not null check (jsonb_typeof(evidence_snapshot) = 'object'),
  observed_at timestamptz not null default now(),
  valid_from date not null,
  valid_until date,
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  observed_amount numeric(18,4) not null check (
    observed_amount >= 0 and observed_amount <> all (
      array['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])),
  primary key (project_id, id),
  check (valid_until is null or valid_until >= valid_from),
  foreign key (project_id, evidence_ref)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index service_rates_history_idx on public.project_service_rates
  (project_id, service_id, observed_at desc);

create table public.project_budgets (
  project_id uuid not null references public.projects(id) on delete restrict,
  id uuid not null default gen_random_uuid(),
  status text not null check (status in ('draft', 'active', 'closed')),
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  revision bigint not null default 1 check (revision > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (project_id, id)
);
create unique index project_one_active_budget_idx on public.project_budgets (project_id) where status = 'active';

create table public.budget_lines (
  project_id uuid not null,
  id uuid not null default gen_random_uuid(),
  budget_id uuid not null,
  entity_id text not null,
  offer_id uuid,
  service_rate_id uuid,
  quantity numeric(18,4) not null check (
    quantity > 0 and quantity <> all (
      array['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])),
  created_at timestamptz not null default now(),
  primary key (project_id, id),
  foreign key (project_id, budget_id)
    references public.project_budgets(project_id, id) on delete restrict,
  foreign key (project_id, entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict,
  foreign key (project_id, offer_id)
    references public.project_offers(project_id, id) on delete restrict,
  foreign key (project_id, service_rate_id)
    references public.project_service_rates(project_id, id) on delete restrict,
  check (num_nonnulls(offer_id, service_rate_id) = 1)
);
create index budget_lines_budget_idx on public.budget_lines (project_id, budget_id);

create table public.proposal_snapshots (
  project_id uuid not null,
  id uuid not null default gen_random_uuid(),
  budget_id uuid not null,
  revision bigint not null check (revision > 0),
  status text not null default 'draft' check (status = 'draft'),
  document jsonb not null check (jsonb_typeof(document) = 'object'),
  created_by uuid not null default auth.uid() references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  primary key (project_id, id),
  unique (project_id, budget_id, revision),
  foreign key (project_id, budget_id)
    references public.project_budgets(project_id, id) on delete restrict
);

create table public.audit_events (
  id bigint generated always as identity primary key,
  project_id uuid not null references public.projects(id) on delete restrict,
  actor_user_id uuid not null references auth.users(id) on delete restrict,
  table_name text not null,
  action text not null check (action in ('INSERT', 'UPDATE', 'DELETE')),
  resource_id text not null,
  occurred_at timestamptz not null default now()
);
create index audit_events_project_time_idx on public.audit_events (project_id, occurred_at desc, id desc);

-- Privado: una clave de comando por proyecto se ata a su payload exacto.
create table private.project_command_receipts (
  project_id uuid not null references public.projects(id) on delete restrict,
  command_key text not null check (length(btrim(command_key)) between 1 and 200),
  actor_user_id uuid not null references auth.users(id) on delete restrict,
  action text not null,
  payload jsonb not null,
  result_id uuid not null,
  created_at timestamptz not null default now(),
  primary key (project_id, command_key)
);
revoke all on private.project_command_receipts from public, anon, authenticated, service_role;

-- Las funciones privadas devuelven solo booleanos y evitan recursión entre políticas.
create function private.is_project_owner(p_project_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select auth.uid() is not null and exists (
    select 1 from public.projects p
    where p.id = p_project_id and p.owner_user_id = auth.uid()
  );
$$;
create function private.can_read_project(p_project_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select auth.uid() is not null and (
    exists (select 1 from public.projects p where p.id = p_project_id and p.owner_user_id = auth.uid())
    or exists (select 1 from public.project_memberships m
               where m.project_id = p_project_id and m.user_id = auth.uid())
  );
$$;
create function private.can_edit_project(p_project_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select auth.uid() is not null and (
    exists (select 1 from public.projects p where p.id = p_project_id and p.owner_user_id = auth.uid())
    or exists (select 1 from public.project_memberships m
               where m.project_id = p_project_id and m.user_id = auth.uid() and m.role = 'editor')
  );
$$;

create function private.prevent_owner_membership()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
  if exists (select 1 from public.projects p
             where p.id = new.project_id and p.owner_user_id = new.user_id) then
    raise exception 'owner cannot also be a member' using errcode = '23514';
  end if;
  return new;
end;
$$;
create trigger memberships_owner_guard
before insert or update on public.project_memberships
for each row execute function private.prevent_owner_membership();

create function private.touch_project()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
  new.revision := old.revision + 1;
  new.updated_at := now();
  return new;
end;
$$;
create trigger projects_touch before update on public.projects
for each row execute function private.touch_project();

create function private.touch_budget()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
  new.revision := old.revision + 1;
  new.updated_at := now();
  return new;
end;
$$;
create trigger budgets_touch before update on public.project_budgets
for each row execute function private.touch_budget();

create function private.guard_entity_revision()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
  if new.revision <> old.revision + 1 then
    raise exception 'entity revision must advance by one' using errcode = '23514';
  end if;
  return new;
end;
$$;
create trigger entities_revision_guard before update on public.project_entities
for each row execute function private.guard_entity_revision();

create function private.audit_project_change()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  actor uuid := auth.uid();
  row_data jsonb;
  tenant uuid;
  resource text;
begin
  if actor is null then
    raise exception 'authenticated actor required for project mutation' using errcode = '28000';
  end if;
  if tg_op = 'DELETE' then row_data := to_jsonb(old); else row_data := to_jsonb(new); end if;
  if tg_table_name = 'projects' then
    tenant := (row_data ->> 'id')::uuid;
  else
    tenant := (row_data ->> 'project_id')::uuid;
  end if;
  resource := coalesce(row_data ->> 'id', row_data ->> 'entity_id',
                       row_data ->> 'package_id', row_data ->> 'user_id',
                       row_data ->> 'source_entity_id',
                       row_data ->> 'requirement_entity_id', row_data ->> 'project_id');
  insert into public.audit_events (project_id, actor_user_id, table_name, action, resource_id)
  values (tenant, actor, tg_table_name, tg_op, resource);
  if tg_op = 'DELETE' then return old; else return new; end if;
end;
$$;

-- La oferta conserva la revisión y contenido de evidencia de ese instante.
create function private.pin_offer_evidence()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  source_row public.project_entities%rowtype;
begin
  select * into source_row from public.project_entities
  where project_id = new.project_id and entity_id = new.evidence_ref
    and kind = 'Evidence' and knowledge_state = 'known';
  if not found then
    raise exception 'known project evidence required' using errcode = '23514';
  end if;
  new.evidence_revision := source_row.revision;
  new.evidence_snapshot := to_jsonb(source_row);
  return new;
end;
$$;

-- Toda mutación dependiente invalida la revisión del proyecto en la misma transacción.
create function private.bump_project_revision()
returns trigger language plpgsql security definer set search_path = '' as $$
declare tenant uuid;
begin
  if tg_op = 'DELETE' then tenant := old.project_id; else tenant := new.project_id; end if;
  update public.projects set revision = revision + 1 where id = tenant;
  if tg_op = 'DELETE' then return old; else return new; end if;
end;
$$;

create function private.bump_budget_revision()
returns trigger language plpgsql security definer set search_path = '' as $$
declare tenant uuid; budget uuid;
begin
  if tg_op = 'DELETE' then
    tenant := old.project_id; budget := old.budget_id;
  else
    tenant := new.project_id; budget := new.budget_id;
  end if;
  update public.project_budgets set revision = revision + 1
  where project_id = tenant and id = budget;
  if tg_op = 'DELETE' then return old; else return new; end if;
end;
$$;

create trigger projects_audit after insert or update or delete on public.projects
for each row execute function private.audit_project_change();
create trigger memberships_audit after insert or update or delete on public.project_memberships
for each row execute function private.audit_project_change();
create trigger entities_audit after insert or update or delete on public.project_entities
for each row execute function private.audit_project_change();
create trigger relations_audit after insert or delete on public.project_relations
for each row execute function private.audit_project_change();
create trigger packages_audit after insert or update or delete on public.project_packages
for each row execute function private.audit_project_change();
create trigger offers_audit after insert on public.project_offers
for each row execute function private.audit_project_change();
create trigger offers_pin_evidence before insert on public.project_offers
for each row execute function private.pin_offer_evidence();
create trigger budgets_audit after insert or update on public.project_budgets
for each row execute function private.audit_project_change();
create trigger budget_lines_audit after insert or update or delete on public.budget_lines
for each row execute function private.audit_project_change();
create trigger snapshots_audit after insert on public.proposal_snapshots
for each row execute function private.audit_project_change();
create trigger customers_audit after insert or update or delete on public.project_customers
for each row execute function private.audit_project_change();
create trigger candidates_audit after insert or update on public.project_candidates
for each row execute function private.audit_project_change();
create trigger evaluations_audit after insert on public.project_evaluations
for each row execute function private.audit_project_change();
create trigger selections_audit after insert or update or delete on public.project_selections
for each row execute function private.audit_project_change();
create trigger rates_audit after insert on public.project_service_rates
for each row execute function private.audit_project_change();
create trigger rates_pin_evidence before insert on public.project_service_rates
for each row execute function private.pin_offer_evidence();

create trigger memberships_revision after insert or update or delete on public.project_memberships
for each row execute function private.bump_project_revision();
create trigger entities_project_revision after insert or update or delete on public.project_entities
for each row execute function private.bump_project_revision();
create trigger relations_project_revision after insert or delete on public.project_relations
for each row execute function private.bump_project_revision();
create trigger packages_project_revision after insert or update or delete on public.project_packages
for each row execute function private.bump_project_revision();
create trigger offers_project_revision after insert on public.project_offers
for each row execute function private.bump_project_revision();
create trigger budgets_project_revision after insert or update on public.project_budgets
for each row execute function private.bump_project_revision();
create trigger budget_lines_budget_revision after insert or update or delete on public.budget_lines
for each row execute function private.bump_budget_revision();
create trigger snapshots_project_revision after insert on public.proposal_snapshots
for each row execute function private.bump_project_revision();
create trigger customers_project_revision after insert or update or delete on public.project_customers
for each row execute function private.bump_project_revision();
create trigger candidates_project_revision after insert or update on public.project_candidates
for each row execute function private.bump_project_revision();
create trigger evaluations_project_revision after insert on public.project_evaluations
for each row execute function private.bump_project_revision();
create trigger selections_project_revision after insert or update or delete on public.project_selections
for each row execute function private.bump_project_revision();
create trigger rates_project_revision after insert on public.project_service_rates
for each row execute function private.bump_project_revision();

-- Proyecto y membresía se mutan exclusivamente desde el backend SQL dedicado.
create function private.create_project(
  p_project_id uuid, p_actor uuid, p_command_key text, p_name text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_project_id is null or p_actor is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'project, actor and command key required' using errcode = '23514';
  end if;
  input_payload := jsonb_build_object('name', p_name);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'create_project' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.projects (id, owner_user_id, name)
  values (p_project_id, p_actor, p_name);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'create_project', input_payload,
          p_project_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_project_id;
end;
$$;

create function private.set_project_member(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_user_id uuid, p_role text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  old_owner uuid;
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_user_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 or
     (p_role is not null and p_role not in ('editor', 'viewer')) then
    raise exception 'valid actor, user, role and key required' using errcode = '23514';
  end if;
  select owner_user_id into old_owner from public.projects
  where id = p_project_id for update;
  if old_owner is null or old_owner <> p_actor then
    raise exception 'project owner required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('user_id', p_user_id, 'role', p_role);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'set_member' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  if p_user_id = old_owner then
    raise exception 'owner cannot be member' using errcode = '23514'; end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  if p_role is null then
    delete from public.project_memberships
    where project_id = p_project_id and user_id = p_user_id;
  else
    insert into public.project_memberships (project_id, user_id, role)
    values (p_project_id, p_user_id, p_role)
    on conflict (project_id, user_id) do update set role = excluded.role;
  end if;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'set_member', input_payload,
          p_user_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_user_id;
end;
$$;

-- Orden de bloqueo común: proyecto FOR UPDATE, luego membresía FOR UPDATE.
create function private.transfer_project_ownership(
  p_project_id uuid, p_actor uuid, p_command_key text, p_new_owner uuid
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  old_owner uuid;
  removed integer;
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_new_owner is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, destination and command key required' using errcode = '23514';
  end if;
  select owner_user_id into old_owner from public.projects where id = p_project_id for update;
  input_payload := jsonb_build_object('new_owner', p_new_owner);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'transfer_owner' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  if old_owner is null or old_owner <> p_actor then
    raise exception 'project owner required' using errcode = '42501';
  end if;
  perform 1 from public.project_memberships
  where project_id = p_project_id and user_id = p_new_owner and role = 'editor'
  for update;
  if not found then
    raise exception 'new owner must be an existing editor' using errcode = '23514';
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  delete from public.project_memberships where project_id = p_project_id and user_id = p_new_owner;
  get diagnostics removed = row_count;
  if removed <> 1 then
    raise exception 'editor membership changed during transfer' using errcode = '40001';
  end if;
  update public.projects set owner_user_id = p_new_owner where id = p_project_id;
  insert into public.project_memberships (project_id, user_id, role)
  values (p_project_id, old_owner, 'editor');
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'transfer_owner', input_payload,
          p_new_owner);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_new_owner;
end;
$$;

-- Solo el backend de confianza puede invocar esta operación. p_actor es el
-- subject de un JWT ya validado por FastAPI; jamás aceptar el actor del cliente.
create function private.record_project_offer(
  p_project_id uuid, p_actor uuid, p_command_key text, p_catalog_item_id uuid,
  p_supplier_id uuid, p_supplier_branch_id uuid, p_source_id uuid,
  p_supplier_ref text, p_valid_from date, p_valid_until date,
  p_currency text, p_unit_price numeric, p_evidence_ref text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514';
  end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships
               where project_id = p_project_id and user_id = p_actor and role = 'editor')
  ) then
    raise exception 'project editor required' using errcode = '42501';
  end if;
  input_payload := jsonb_build_object(
    'catalog_item_id', p_catalog_item_id, 'supplier_id', p_supplier_id,
    'supplier_branch_id', p_supplier_branch_id, 'source_id', p_source_id,
    'supplier_ref', p_supplier_ref,
    'valid_from', p_valid_from, 'valid_until', p_valid_until,
    'currency', p_currency, 'unit_price', p_unit_price, 'evidence_ref', p_evidence_ref);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_offer' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused with different command' using errcode = '23505';
    end if;
    return prior.result_id;
  end if;
  if not exists (select 1 from public.project_entities
                 where project_id = p_project_id and entity_id = p_evidence_ref
                   and kind = 'Evidence' and knowledge_state = 'known') then
    raise exception 'known project evidence required' using errcode = '23514';
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_offers
    (project_id, catalog_item_id, supplier_id, supplier_branch_id, source_id,
     supplier_ref, valid_from, valid_until,
     currency, unit_price, evidence_ref)
  values (p_project_id, p_catalog_item_id, p_supplier_id, p_supplier_branch_id,
          p_source_id, p_supplier_ref, p_valid_from,
          p_valid_until, p_currency, p_unit_price, p_evidence_ref)
  returning id into new_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_offer', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

-- La selección y evaluación son comandos separados; no se ofrece SQL dinámico.
create function private.record_project_candidate(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_requirement text, p_catalog_item_id uuid, p_evidence_ref text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514';
  end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships
               where project_id = p_project_id and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  if not exists (select 1 from public.project_entities
                 where project_id = p_project_id and entity_id = p_requirement
                   and kind = 'Requirement') or
     not exists (select 1 from public.project_entities
                 where project_id = p_project_id and entity_id = p_evidence_ref
                   and kind = 'Evidence' and knowledge_state = 'known') then
    raise exception 'requirement and known evidence required' using errcode = '23514';
  end if;
  input_payload := jsonb_build_object('requirement', p_requirement,
    'catalog_item_id', p_catalog_item_id, 'evidence_ref', p_evidence_ref);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_candidate' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_candidates
    (project_id, requirement_entity_id, catalog_item_id, status, evidence_ref)
  values (p_project_id, p_requirement, p_catalog_item_id, 'proposed', p_evidence_ref);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_candidate', input_payload,
          p_catalog_item_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_catalog_item_id;
end;
$$;

create function private.record_project_evaluation(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_requirement text, p_catalog_item_id uuid, p_evidence_ref text,
  p_outcome text, p_rationale text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514';
  end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships
               where project_id = p_project_id and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  if not exists (select 1 from public.project_entities
                 where project_id = p_project_id and entity_id = p_evidence_ref
                   and kind = 'Evidence' and knowledge_state = 'known') then
    raise exception 'known evidence required' using errcode = '23514'; end if;
  input_payload := jsonb_build_object('requirement', p_requirement,
    'catalog_item_id', p_catalog_item_id, 'evidence_ref', p_evidence_ref,
    'outcome', p_outcome, 'rationale', p_rationale);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_evaluation' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_evaluations
    (project_id, requirement_entity_id, catalog_item_id, evidence_ref, outcome, rationale)
  values (p_project_id, p_requirement, p_catalog_item_id, p_evidence_ref,
          p_outcome, p_rationale) returning id into new_id;
  if p_outcome = 'rejected' then
    update public.project_selections
    set status = 'superseded', superseded_at = clock_timestamp()
    where project_id = p_project_id and requirement_entity_id = p_requirement
      and catalog_item_id = p_catalog_item_id and status = 'active';
    update public.project_candidates set status = 'rejected'
    where project_id = p_project_id and requirement_entity_id = p_requirement
      and catalog_item_id = p_catalog_item_id;
  elsif p_outcome = 'accepted' then
    update public.project_candidates set status = 'proposed'
    where project_id = p_project_id and requirement_entity_id = p_requirement
      and catalog_item_id = p_catalog_item_id and status = 'rejected';
  end if;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_evaluation', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

create function private.select_project_candidate(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_requirement text, p_catalog_item_id uuid, p_evaluation_id uuid
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514';
  end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships
               where project_id = p_project_id and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('requirement', p_requirement,
    'catalog_item_id', p_catalog_item_id, 'evaluation_id', p_evaluation_id);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'select_candidate' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  if not exists (select 1 from public.project_evaluations e
                 where e.project_id = p_project_id and e.id = p_evaluation_id
                   and e.requirement_entity_id = p_requirement
                   and e.catalog_item_id = p_catalog_item_id and e.outcome = 'accepted'
                   and e.id = (select latest.id from public.project_evaluations latest
                               where latest.project_id = p_project_id
                                 and latest.requirement_entity_id = p_requirement
                                 and latest.catalog_item_id = p_catalog_item_id
                               order by latest.evaluation_seq desc limit 1)) then
    raise exception 'latest accepted evaluation required' using errcode = '23514';
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  update public.project_selections
  set status = 'superseded', superseded_at = clock_timestamp()
  where project_id = p_project_id and requirement_entity_id = p_requirement
    and status = 'active';
  update public.project_candidates set status = 'proposed'
  where project_id = p_project_id and requirement_entity_id = p_requirement
    and status = 'selected';
  update public.project_candidates set status = 'selected'
  where project_id = p_project_id and requirement_entity_id = p_requirement
    and catalog_item_id = p_catalog_item_id and status = 'proposed';
  if not found then raise exception 'proposed candidate required' using errcode = '23514'; end if;
  insert into public.project_selections
    (project_id, requirement_entity_id, catalog_item_id, evaluation_id)
  values (p_project_id, p_requirement, p_catalog_item_id, p_evaluation_id);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'select_candidate', input_payload,
          p_catalog_item_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_catalog_item_id;
end;
$$;

create function private.record_project_service_rate(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_service_id uuid, p_source_id uuid, p_evidence_ref text,
  p_valid_from date, p_valid_until date, p_currency text, p_amount numeric
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('service_id', p_service_id, 'source_id', p_source_id,
    'evidence_ref', p_evidence_ref, 'valid_from', p_valid_from,
    'valid_until', p_valid_until, 'currency', p_currency, 'amount', p_amount);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_service_rate' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_service_rates
    (project_id, service_id, source_id, evidence_ref, valid_from, valid_until,
     currency, observed_amount)
  values (p_project_id, p_service_id, p_source_id, p_evidence_ref, p_valid_from,
          p_valid_until, p_currency, p_amount) returning id into new_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_service_rate', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

create function private.create_project_budget(
  p_project_id uuid, p_actor uuid, p_command_key text, p_currency text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb := jsonb_build_object('currency', p_currency);
  prior private.project_command_receipts%rowtype;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'create_budget' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_budgets (project_id, status, currency)
  values (p_project_id, 'draft', p_currency) returning id into new_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'create_budget', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

create function private.add_project_budget_line(
  p_project_id uuid, p_actor uuid, p_command_key text, p_budget_id uuid,
  p_expected_revision bigint, p_entity_id text, p_offer_id uuid,
  p_service_rate_id uuid, p_quantity numeric
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  current_status text;
  current_revision bigint;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('budget_id', p_budget_id,
    'expected_revision', p_expected_revision, 'entity_id', p_entity_id,
    'offer_id', p_offer_id, 'service_rate_id', p_service_rate_id,
    'quantity', p_quantity);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'add_budget_line' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  select status, revision into current_status, current_revision
  from public.project_budgets where project_id = p_project_id and id = p_budget_id for update;
  if current_status is distinct from 'draft' or
     current_revision is distinct from p_expected_revision then
    raise exception 'draft budget and current revision required' using errcode = '40001'; end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.budget_lines
    (project_id, budget_id, entity_id, offer_id, service_rate_id, quantity)
  values (p_project_id, p_budget_id, p_entity_id, p_offer_id, p_service_rate_id, p_quantity)
  returning id into new_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'add_budget_line', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

create function private.transition_project_budget(
  p_project_id uuid, p_actor uuid, p_command_key text, p_budget_id uuid,
  p_expected_revision bigint, p_status text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  current_status text;
  current_revision bigint;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('budget_id', p_budget_id,
    'expected_revision', p_expected_revision, 'status', p_status);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'transition_budget' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  select status, revision into current_status, current_revision
  from public.project_budgets where project_id = p_project_id and id = p_budget_id for update;
  if current_revision is distinct from p_expected_revision or
     not ((current_status = 'draft' and p_status = 'active') or
          (current_status = 'active' and p_status = 'closed')) then
    raise exception 'valid transition and current revision required' using errcode = '40001';
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  update public.project_budgets set status = p_status
  where project_id = p_project_id and id = p_budget_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'transition_budget', input_payload,
          p_budget_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return p_budget_id;
end;
$$;

-- Proyección canónica de borrador; no habilita emisión ni aceptación comercial.
create function private.capture_budget_draft(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_budget_id uuid, p_expected_revision bigint
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  current_status text;
  current_revision bigint;
  lines_json jsonb;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('budget_id', p_budget_id,
    'expected_revision', p_expected_revision);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'capture_budget_draft' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  select status, revision into current_status, current_revision
  from public.project_budgets where project_id = p_project_id and id = p_budget_id for update;
  if current_status is distinct from 'active' or
     current_revision is distinct from p_expected_revision then
    raise exception 'active budget and current revision required' using errcode = '40001'; end if;
  select coalesce(jsonb_agg(jsonb_build_object(
    'line_id', l.id, 'entity_id', l.entity_id, 'quantity', l.quantity,
    'offer', to_jsonb(o), 'service_rate', to_jsonb(r)) order by l.id), '[]'::jsonb)
  into lines_json
  from public.budget_lines l
  left join public.project_offers o on o.project_id = l.project_id and o.id = l.offer_id
  left join public.project_service_rates r on r.project_id = l.project_id
    and r.id = l.service_rate_id
  where l.project_id = p_project_id and l.budget_id = p_budget_id;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.proposal_snapshots
    (project_id, budget_id, revision, document, created_by)
  values (p_project_id, p_budget_id, p_expected_revision,
          jsonb_build_object('budget_id', p_budget_id,
            'budget_revision', p_expected_revision, 'lines', lines_json), p_actor)
  returning id into new_id;
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'capture_budget_draft', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

create function private.record_project_customer(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_customer_ref text, p_country_code char(2),
  p_legal_name text, p_contact_email text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  new_id uuid;
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('customer_ref', p_customer_ref,
    'country_code', p_country_code, 'legal_name', p_legal_name,
    'contact_email', p_contact_email);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_customer' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_customers (project_id, customer_ref, country_code)
  values (p_project_id, p_customer_ref, p_country_code) returning id into new_id;
  insert into private.customer_profiles
    (project_id, customer_id, legal_name, contact_email)
  values (p_project_id, new_id, p_legal_name, p_contact_email);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_customer', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

-- Solo declaraciones de usuario de tipos no normativos. El backend no puede
-- insertar Evidence/Approval/Rule ni paquetes arbitrarios con esta función.
create function private.record_project_statement(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_kind text, p_label text, p_details jsonb
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  new_id uuid := gen_random_uuid();
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 or
     p_kind not in ('ProjectGoal', 'Requirement', 'Constraint', 'SiteCondition',
                    'Task', 'Deliverable') then
    raise exception 'valid user statement and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('kind', p_kind, 'label', p_label,
    'details', p_details);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_statement' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_entities
    (project_id, entity_id, kind, label, origin_kind, origin_ref,
     scope_kind, scope_id, revision, knowledge_state, details)
  values (p_project_id, new_id::text, p_kind, p_label, 'user', p_actor::text,
          'project', p_project_id::text, 1, 'assumed', p_details);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_statement', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

-- La fuente debe existir en el catálogo compartido curado por el migrador.
create function private.record_project_evidence(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_source_id uuid, p_label text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  source_row public.research_sources%rowtype;
  new_id uuid := gen_random_uuid();
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('source_id', p_source_id, 'label', p_label);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'record_evidence' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  select * into source_row from public.research_sources where id = p_source_id;
  if not found then
    raise exception 'curated source required' using errcode = '23514'; end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_entities
    (project_id, entity_id, kind, label, origin_kind, origin_ref,
     scope_kind, scope_id, revision, knowledge_state, details)
  values (p_project_id, new_id::text, 'Evidence', p_label, 'document',
          source_row.source_ref, 'project', p_project_id::text, 1, 'known',
          jsonb_build_object('source', to_jsonb(source_row)));
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'record_evidence', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

-- Los hechos se copian de una versión global curada; el cliente no los aporta.
create function private.attach_project_package(
  p_project_id uuid, p_actor uuid, p_command_key text,
  p_namespace text, p_version text, p_subject_entity_id text
)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  input_payload jsonb;
  prior private.project_command_receipts%rowtype;
  curated_facts jsonb;
  new_id uuid := gen_random_uuid();
  previous_claim text := current_setting('request.jwt.claim.sub', true);
begin
  if p_actor is null or p_project_id is null or p_command_key is null or
     length(btrim(p_command_key)) not between 1 and 200 then
    raise exception 'actor, project and command key required' using errcode = '23514'; end if;
  perform 1 from public.projects where id = p_project_id for update;
  if not found or not (
    exists (select 1 from public.projects where id = p_project_id and owner_user_id = p_actor)
    or exists (select 1 from public.project_memberships where project_id = p_project_id
               and user_id = p_actor and role = 'editor')
  ) then raise exception 'project editor required' using errcode = '42501'; end if;
  input_payload := jsonb_build_object('namespace', p_namespace, 'version', p_version,
    'subject_entity_id', p_subject_entity_id);
  select * into prior from private.project_command_receipts
  where project_id = p_project_id and command_key = p_command_key;
  if found then
    if prior.actor_user_id <> p_actor or prior.action <> 'attach_package' or
       prior.payload <> input_payload then
      raise exception 'idempotency key reused' using errcode = '23505'; end if;
    return prior.result_id;
  end if;
  select facts into curated_facts from public.knowledge_package_versions
  where namespace = p_namespace and version = p_version;
  if not found then raise exception 'curated package required' using errcode = '23514'; end if;
  perform set_config('request.jwt.claim.sub', p_actor::text, true);
  insert into public.project_packages
    (project_id, package_id, namespace, version, subject_entity_id, facts)
  values (p_project_id, new_id::text, p_namespace, p_version,
          p_subject_entity_id, curated_facts);
  insert into private.project_command_receipts
    (project_id, command_key, actor_user_id, action, payload, result_id)
  values (p_project_id, p_command_key, p_actor, 'attach_package', input_payload, new_id);
  perform set_config('request.jwt.claim.sub', coalesce(previous_claim, ''), true);
  return new_id;
end;
$$;

-- RLS para toda tabla nueva en public. audit_events no usa FORCE: su trigger
-- privado necesita insertar como propietario privilegiado aun sin política INSERT.
alter table public.projects enable row level security;
alter table public.project_memberships enable row level security;
alter table public.catalog_items enable row level security;
alter table public.countries enable row level security;
alter table public.suppliers enable row level security;
alter table public.supplier_branches enable row level security;
alter table public.research_sources enable row level security;
alter table public.product_equivalences enable row level security;
alter table public.product_specs enable row level security;
alter table public.product_warranties enable row level security;
alter table public.knowledge_package_versions enable row level security;
alter table public.service_definitions enable row level security;
alter table public.project_customers enable row level security;
alter table public.project_entities enable row level security;
alter table public.project_relations enable row level security;
alter table public.project_packages enable row level security;
alter table public.project_candidates enable row level security;
alter table public.project_evaluations enable row level security;
alter table public.project_selections enable row level security;
alter table public.project_offers enable row level security;
alter table public.project_service_rates enable row level security;
alter table public.project_budgets enable row level security;
alter table public.budget_lines enable row level security;
alter table public.proposal_snapshots enable row level security;
alter table public.audit_events enable row level security;
alter table private.supplier_contacts enable row level security;
alter table private.customer_profiles enable row level security;
alter table public.projects force row level security;
alter table public.project_memberships force row level security;
alter table public.catalog_items force row level security;
alter table public.countries force row level security;
alter table public.suppliers force row level security;
alter table public.supplier_branches force row level security;
alter table public.research_sources force row level security;
alter table public.product_equivalences force row level security;
alter table public.product_specs force row level security;
alter table public.product_warranties force row level security;
alter table public.knowledge_package_versions force row level security;
alter table public.service_definitions force row level security;
alter table public.project_customers force row level security;
alter table public.project_entities force row level security;
alter table public.project_relations force row level security;
alter table public.project_packages force row level security;
alter table public.project_candidates force row level security;
alter table public.project_evaluations force row level security;
alter table public.project_selections force row level security;
alter table public.project_offers force row level security;
alter table public.project_service_rates force row level security;
alter table public.project_budgets force row level security;
alter table public.budget_lines force row level security;
alter table public.proposal_snapshots force row level security;
alter table private.supplier_contacts force row level security;
alter table private.customer_profiles force row level security;

create policy projects_read on public.projects for select to authenticated
using (private.can_read_project(id));
create policy projects_policy_owner on public.projects for select to at208_policy_owner
using (true);
create policy projects_mutator_read on public.projects for select to at208_mutation_owner
using (true);
create policy projects_mutator_insert on public.projects for insert to at208_mutation_owner
with check (true);
create policy projects_mutator_update on public.projects for update to at208_mutation_owner
using (true) with check (true);

create policy memberships_read on public.project_memberships for select to authenticated
using (private.can_read_project(project_id));
create policy memberships_policy_owner on public.project_memberships for select to at208_policy_owner
using (true);
create policy memberships_mutator_read on public.project_memberships for select to at208_mutation_owner
using (true);
create policy memberships_mutator_insert on public.project_memberships for insert to at208_mutation_owner
with check (true);
create policy memberships_mutator_update on public.project_memberships for update to at208_mutation_owner
using (true) with check (true);
create policy memberships_mutator_delete on public.project_memberships for delete to at208_mutation_owner
using (true);

create policy catalog_read on public.catalog_items for select to authenticated
using ((select auth.uid()) is not null);
create policy countries_read on public.countries for select to authenticated
using ((select auth.uid()) is not null);
create policy suppliers_read on public.suppliers for select to authenticated
using ((select auth.uid()) is not null);
create policy branches_read on public.supplier_branches for select to authenticated
using ((select auth.uid()) is not null);
create policy sources_read on public.research_sources for select to authenticated
using ((select auth.uid()) is not null);
create policy sources_mutator_read on public.research_sources for select to at208_mutation_owner
using (true);
create policy equivalences_read on public.product_equivalences for select to authenticated
using ((select auth.uid()) is not null);
create policy specs_read on public.product_specs for select to authenticated
using ((select auth.uid()) is not null);
create policy warranties_read on public.product_warranties for select to authenticated
using ((select auth.uid()) is not null);
create policy knowledge_packages_read on public.knowledge_package_versions for select to authenticated
using ((select auth.uid()) is not null);
create policy knowledge_packages_mutator_read on public.knowledge_package_versions
for select to at208_mutation_owner using (true);
create policy services_read on public.service_definitions for select to authenticated
using ((select auth.uid()) is not null);
create policy customers_read on public.project_customers for select to authenticated
using (private.can_read_project(project_id));
create policy customers_mutator_read on public.project_customers for select to at208_mutation_owner
using (true);
create policy customers_mutator_insert on public.project_customers for insert to at208_mutation_owner
with check (true);
create policy customer_profiles_mutator_insert on private.customer_profiles
for insert to at208_mutation_owner with check (true);

create policy entities_read on public.project_entities for select to authenticated
using (private.can_read_project(project_id));
create policy entities_mutator_read on public.project_entities for select to at208_mutation_owner
using (true);
create policy entities_mutator_insert on public.project_entities for insert to at208_mutation_owner
with check (true);

create policy relations_read on public.project_relations for select to authenticated
using (private.can_read_project(project_id));

create policy packages_read on public.project_packages for select to authenticated
using (private.can_read_project(project_id));
create policy packages_mutator_insert on public.project_packages for insert to at208_mutation_owner
with check (true);

create policy candidates_read on public.project_candidates for select to authenticated
using (private.can_read_project(project_id));
create policy candidates_mutator_read on public.project_candidates for select to at208_mutation_owner
using (true);
create policy candidates_mutator_insert on public.project_candidates for insert to at208_mutation_owner
with check (true);
create policy candidates_mutator_update on public.project_candidates for update to at208_mutation_owner
using (true) with check (true);
create policy evaluations_read on public.project_evaluations for select to authenticated
using (private.can_read_project(project_id));
create policy evaluations_mutator_read on public.project_evaluations for select to at208_mutation_owner
using (true);
create policy evaluations_mutator_insert on public.project_evaluations for insert to at208_mutation_owner
with check (true);
create policy selections_read on public.project_selections for select to authenticated
using (private.can_read_project(project_id));
create policy selections_mutator_read on public.project_selections for select to at208_mutation_owner
using (true);
create policy selections_mutator_insert on public.project_selections for insert to at208_mutation_owner
with check (true);
create policy selections_mutator_update on public.project_selections for update to at208_mutation_owner
using (true) with check (true);

create policy offers_read on public.project_offers for select to authenticated
using (private.can_read_project(project_id));
create policy offers_mutator_read on public.project_offers for select to at208_mutation_owner
using (true);
create policy offers_mutator_insert on public.project_offers for insert to at208_mutation_owner
with check (true);
create policy rates_read on public.project_service_rates for select to authenticated
using (private.can_read_project(project_id));
create policy rates_mutator_read on public.project_service_rates for select to at208_mutation_owner
using (true);
create policy rates_mutator_insert on public.project_service_rates for insert to at208_mutation_owner
with check (true);

create policy budgets_read on public.project_budgets for select to authenticated
using (private.can_read_project(project_id));
create policy budgets_mutator_read on public.project_budgets for select to at208_mutation_owner
using (true);
create policy budgets_mutator_insert on public.project_budgets for insert to at208_mutation_owner
with check (true);
create policy budgets_mutator_update on public.project_budgets for update to at208_mutation_owner
using (true) with check (true);

create policy budget_lines_read on public.budget_lines for select to authenticated
using (private.can_read_project(project_id));
create policy budget_lines_mutator_read on public.budget_lines for select to at208_mutation_owner
using (true);
create policy budget_lines_mutator_insert on public.budget_lines for insert to at208_mutation_owner
with check (true);

create policy snapshots_read on public.proposal_snapshots for select to authenticated
using (private.can_read_project(project_id));
create policy snapshots_mutator_read on public.proposal_snapshots for select to at208_mutation_owner
using (true);
create policy snapshots_mutator_insert on public.proposal_snapshots for insert to at208_mutation_owner
with check (true);
create policy audit_read on public.audit_events for select to authenticated
using (private.is_project_owner(project_id));
create policy audit_owner_insert on public.audit_events for insert to at208_audit_owner
with check (true);

-- Los roles de cliente no reciben escrituras de catálogo, historial ni auditoría.
revoke all on table public.projects, public.project_memberships, public.catalog_items,
  public.countries, public.suppliers, public.supplier_branches,
  public.research_sources, public.product_equivalences, public.product_specs, public.product_warranties,
  public.knowledge_package_versions,
  public.service_definitions, public.project_customers,
  public.project_entities, public.project_relations, public.project_packages,
  public.project_candidates, public.project_evaluations, public.project_selections,
  public.project_offers, public.project_service_rates, public.project_budgets, public.budget_lines,
  public.proposal_snapshots, public.audit_events
  from public, anon, authenticated, service_role, at208_backend;
revoke all on table private.supplier_contacts, private.customer_profiles
  from public, anon, authenticated, service_role, at208_backend;
grant select on table public.projects, public.project_memberships, public.catalog_items,
  public.countries, public.suppliers, public.supplier_branches,
  public.research_sources, public.product_equivalences, public.product_specs, public.product_warranties,
  public.knowledge_package_versions,
  public.service_definitions, public.project_customers,
  public.project_entities, public.project_relations, public.project_packages,
  public.project_candidates, public.project_evaluations, public.project_selections,
  public.project_offers, public.project_service_rates, public.project_budgets, public.budget_lines,
  public.proposal_snapshots, public.audit_events to authenticated;
grant select on public.projects, public.project_memberships to at208_policy_owner;
grant select on public.projects, public.project_memberships, public.project_entities,
  public.project_candidates, public.project_evaluations, public.project_customers,
  public.research_sources, public.knowledge_package_versions,
  public.project_offers,
  public.project_service_rates, public.project_budgets, public.budget_lines,
  public.proposal_snapshots, public.project_selections
  to at208_mutation_owner;
grant insert (id, owner_user_id, name) on public.projects to at208_mutation_owner;
grant update (owner_user_id, revision, updated_at) on public.projects to at208_mutation_owner;
grant insert (project_id, user_id, role) on public.project_memberships to at208_mutation_owner;
grant update (role) on public.project_memberships to at208_mutation_owner;
grant delete on public.project_memberships to at208_mutation_owner;
grant insert on public.project_offers to at208_mutation_owner;
grant insert on public.project_service_rates to at208_mutation_owner;
grant insert on public.project_candidates to at208_mutation_owner;
grant insert on public.project_entities to at208_mutation_owner;
grant insert on public.project_packages to at208_mutation_owner;
grant update (status) on public.project_candidates to at208_mutation_owner;
grant insert on public.project_evaluations, public.project_selections to at208_mutation_owner;
grant update (status, superseded_at) on public.project_selections to at208_mutation_owner;
grant insert on public.project_budgets, public.budget_lines to at208_mutation_owner;
grant insert on public.project_customers, private.customer_profiles to at208_mutation_owner;
grant insert on public.proposal_snapshots to at208_mutation_owner;
grant update (revision, updated_at, status) on public.project_budgets to at208_mutation_owner;
grant select, insert on private.project_command_receipts to at208_mutation_owner;
grant insert on public.audit_events to at208_audit_owner;
-- Las escrituras de dominio/evidencia/comercio se reservan a funciones privadas
-- de servicio nombradas. No hay escritura arbitraria de hechos ni emisión.

revoke all on function private.is_project_owner(uuid), private.can_read_project(uuid),
  private.can_edit_project(uuid),
  private.create_project(uuid, uuid, text, text),
  private.set_project_member(uuid, uuid, text, uuid, text),
  private.transfer_project_ownership(uuid, uuid, text, uuid),
  private.prevent_owner_membership(), private.touch_project(), private.touch_budget(),
  private.guard_entity_revision(), private.audit_project_change(),
  private.pin_offer_evidence(),
  private.bump_project_revision(), private.bump_budget_revision(),
  private.record_project_offer(uuid, uuid, text, uuid, uuid, uuid, uuid, text, date, date, text, numeric, text),
  private.record_project_candidate(uuid, uuid, text, text, uuid, text),
  private.record_project_evaluation(uuid, uuid, text, text, uuid, text, text, text),
  private.select_project_candidate(uuid, uuid, text, text, uuid, uuid),
  private.record_project_service_rate(uuid, uuid, text, uuid, uuid, text, date, date, text, numeric),
  private.create_project_budget(uuid, uuid, text, text),
  private.add_project_budget_line(uuid, uuid, text, uuid, bigint, text, uuid, uuid, numeric),
  private.transition_project_budget(uuid, uuid, text, uuid, bigint, text),
  private.capture_budget_draft(uuid, uuid, text, uuid, bigint),
  private.record_project_customer(uuid, uuid, text, text, character, text, text),
  private.record_project_statement(uuid, uuid, text, text, text, jsonb),
  private.record_project_evidence(uuid, uuid, text, uuid, text),
  private.attach_project_package(uuid, uuid, text, text, text, text)
  from public, anon, authenticated, service_role, at208_backend;
grant execute on function private.is_project_owner(uuid), private.can_read_project(uuid),
  private.can_edit_project(uuid)
  to authenticated;
grant execute on function private.create_project(uuid, uuid, text, text),
  private.set_project_member(uuid, uuid, text, uuid, text),
  private.transfer_project_ownership(uuid, uuid, text, uuid) to at208_backend;
grant execute on function private.record_project_offer(
  uuid, uuid, text, uuid, uuid, uuid, uuid, text, date, date, text, numeric, text) to at208_backend;
grant execute on function private.record_project_candidate(
  uuid, uuid, text, text, uuid, text) to at208_backend;
grant execute on function private.record_project_evaluation(
  uuid, uuid, text, text, uuid, text, text, text) to at208_backend;
grant execute on function private.select_project_candidate(
  uuid, uuid, text, text, uuid, uuid) to at208_backend;
grant execute on function private.record_project_service_rate(
  uuid, uuid, text, uuid, uuid, text, date, date, text, numeric) to at208_backend;
grant execute on function private.create_project_budget(uuid, uuid, text, text),
  private.add_project_budget_line(uuid, uuid, text, uuid, bigint, text, uuid, uuid, numeric),
  private.transition_project_budget(uuid, uuid, text, uuid, bigint, text),
  private.capture_budget_draft(uuid, uuid, text, uuid, bigint),
  private.record_project_customer(uuid, uuid, text, text, character, text, text),
  private.record_project_statement(uuid, uuid, text, text, text, jsonb),
  private.record_project_evidence(uuid, uuid, text, uuid, text),
  private.attach_project_package(uuid, uuid, text, text, text, text)
  to at208_backend;
alter function private.is_project_owner(uuid) owner to at208_policy_owner;
alter function private.can_read_project(uuid) owner to at208_policy_owner;
alter function private.can_edit_project(uuid) owner to at208_policy_owner;
alter function private.audit_project_change() owner to at208_audit_owner;
alter function private.pin_offer_evidence() owner to at208_mutation_owner;
alter function private.bump_project_revision() owner to at208_mutation_owner;
alter function private.bump_budget_revision() owner to at208_mutation_owner;
alter function private.create_project(uuid, uuid, text, text) owner to at208_mutation_owner;
alter function private.set_project_member(uuid, uuid, text, uuid, text)
  owner to at208_mutation_owner;
alter function private.transfer_project_ownership(uuid, uuid, text, uuid)
  owner to at208_mutation_owner;
alter function private.record_project_offer(
  uuid, uuid, text, uuid, uuid, uuid, uuid, text, date, date, text, numeric, text)
  owner to at208_mutation_owner;
alter function private.record_project_candidate(uuid, uuid, text, text, uuid, text)
  owner to at208_mutation_owner;
alter function private.record_project_evaluation(uuid, uuid, text, text, uuid, text, text, text)
  owner to at208_mutation_owner;
alter function private.select_project_candidate(uuid, uuid, text, text, uuid, uuid)
  owner to at208_mutation_owner;
alter function private.record_project_service_rate(
  uuid, uuid, text, uuid, uuid, text, date, date, text, numeric)
  owner to at208_mutation_owner;
alter function private.create_project_budget(uuid, uuid, text, text)
  owner to at208_mutation_owner;
alter function private.add_project_budget_line(
  uuid, uuid, text, uuid, bigint, text, uuid, uuid, numeric)
  owner to at208_mutation_owner;
alter function private.transition_project_budget(uuid, uuid, text, uuid, bigint, text)
  owner to at208_mutation_owner;
alter function private.capture_budget_draft(uuid, uuid, text, uuid, bigint)
  owner to at208_mutation_owner;
alter function private.record_project_customer(
  uuid, uuid, text, text, character, text, text) owner to at208_mutation_owner;
alter function private.record_project_statement(uuid, uuid, text, text, text, jsonb)
  owner to at208_mutation_owner;
alter function private.record_project_evidence(uuid, uuid, text, uuid, text)
  owner to at208_mutation_owner;
alter function private.attach_project_package(uuid, uuid, text, text, text, text)
  owner to at208_mutation_owner;

commit;
