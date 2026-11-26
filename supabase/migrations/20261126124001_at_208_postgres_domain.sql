-- AT-208: proyecto universal, historia comercial e aislamiento por proyecto.
-- Requiere roles Supabase anon/authenticated y auth.uid()/auth.users.
begin;

create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;

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
  sku text not null check (length(btrim(sku)) > 0),
  label text not null check (length(btrim(label)) > 0),
  facts jsonb not null default '{}'::jsonb check (jsonb_typeof(facts) = 'object'),
  created_at timestamptz not null default now(),
  unique (namespace, version, sku)
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
  foreign key (project_id, subject_entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict
);
create index project_packages_subject_idx on public.project_packages (project_id, subject_entity_id);

create table public.project_offers (
  project_id uuid not null references public.projects(id) on delete restrict,
  id uuid not null default gen_random_uuid(),
  catalog_item_id uuid not null references public.catalog_items(id) on delete restrict,
  supplier_ref text not null check (length(btrim(supplier_ref)) > 0),
  observed_at timestamptz not null default now(),
  valid_from date not null,
  valid_until date,
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  unit_price numeric(18,4) not null check (unit_price >= 0),
  evidence_ref text not null check (length(btrim(evidence_ref)) > 0),
  primary key (project_id, id),
  check (valid_until is null or valid_until >= valid_from)
);
create index project_offers_history_idx on public.project_offers (project_id, catalog_item_id, observed_at desc);

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
  quantity numeric(18,4) not null check (quantity > 0),
  created_at timestamptz not null default now(),
  primary key (project_id, id),
  foreign key (project_id, budget_id)
    references public.project_budgets(project_id, id) on delete restrict,
  foreign key (project_id, entity_id)
    references public.project_entities(project_id, entity_id) on delete restrict,
  foreign key (project_id, offer_id)
    references public.project_offers(project_id, id) on delete restrict
);
create index budget_lines_budget_idx on public.budget_lines (project_id, budget_id);

create table public.proposal_snapshots (
  project_id uuid not null,
  id uuid not null default gen_random_uuid(),
  budget_id uuid not null,
  revision bigint not null check (revision > 0),
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
                       row_data ->> 'source_entity_id');
  insert into public.audit_events (project_id, actor_user_id, table_name, action, resource_id)
  values (tenant, actor, tg_table_name, tg_op, resource);
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
create trigger budgets_audit after insert or update on public.project_budgets
for each row execute function private.audit_project_change();
create trigger budget_lines_audit after insert or update or delete on public.budget_lines
for each row execute function private.audit_project_change();
create trigger snapshots_audit after insert on public.proposal_snapshots
for each row execute function private.audit_project_change();

-- Transferencia atómica: destino debe ser editor, sin cambiar propietario por UPDATE directo.
create function private.transfer_project_ownership(p_project_id uuid, p_new_owner uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare
  old_owner uuid;
begin
  if auth.uid() is null then
    raise exception 'authenticated actor required' using errcode = '28000';
  end if;
  select owner_user_id into old_owner from public.projects where id = p_project_id for update;
  if old_owner is null or old_owner <> auth.uid() then
    raise exception 'project owner required' using errcode = '42501';
  end if;
  if not exists (select 1 from public.project_memberships
                 where project_id = p_project_id and user_id = p_new_owner and role = 'editor') then
    raise exception 'new owner must be an existing editor' using errcode = '23514';
  end if;
  delete from public.project_memberships where project_id = p_project_id and user_id = p_new_owner;
  update public.projects set owner_user_id = p_new_owner where id = p_project_id;
  insert into public.project_memberships (project_id, user_id, role)
  values (p_project_id, old_owner, 'editor');
end;
$$;

-- RLS para toda tabla nueva en public. audit_events no usa FORCE: su trigger
-- privado necesita insertar como propietario privilegiado aun sin política INSERT.
alter table public.projects enable row level security;
alter table public.project_memberships enable row level security;
alter table public.catalog_items enable row level security;
alter table public.project_entities enable row level security;
alter table public.project_relations enable row level security;
alter table public.project_packages enable row level security;
alter table public.project_offers enable row level security;
alter table public.project_budgets enable row level security;
alter table public.budget_lines enable row level security;
alter table public.proposal_snapshots enable row level security;
alter table public.audit_events enable row level security;
alter table public.projects force row level security;
alter table public.project_memberships force row level security;
alter table public.catalog_items force row level security;
alter table public.project_entities force row level security;
alter table public.project_relations force row level security;
alter table public.project_packages force row level security;
alter table public.project_offers force row level security;
alter table public.project_budgets force row level security;
alter table public.budget_lines force row level security;
alter table public.proposal_snapshots force row level security;

create policy projects_read on public.projects for select to authenticated
using (private.can_read_project(id));
create policy projects_insert on public.projects for insert to authenticated
with check (owner_user_id = (select auth.uid()));
create policy projects_update on public.projects for update to authenticated
using (private.can_edit_project(id)) with check (private.can_edit_project(id));

create policy memberships_read on public.project_memberships for select to authenticated
using (private.can_read_project(project_id));
create policy memberships_insert on public.project_memberships for insert to authenticated
with check (private.is_project_owner(project_id));
create policy memberships_update on public.project_memberships for update to authenticated
using (private.is_project_owner(project_id)) with check (private.is_project_owner(project_id));
create policy memberships_delete on public.project_memberships for delete to authenticated
using (private.is_project_owner(project_id));

create policy catalog_read on public.catalog_items for select to authenticated
using ((select auth.uid()) is not null);

create policy entities_read on public.project_entities for select to authenticated
using (private.can_read_project(project_id));
create policy entities_insert on public.project_entities for insert to authenticated
with check (private.can_edit_project(project_id));
create policy entities_update on public.project_entities for update to authenticated
using (private.can_edit_project(project_id)) with check (private.can_edit_project(project_id));
create policy entities_delete on public.project_entities for delete to authenticated
using (private.can_edit_project(project_id));

create policy relations_read on public.project_relations for select to authenticated
using (private.can_read_project(project_id));
create policy relations_insert on public.project_relations for insert to authenticated
with check (private.can_edit_project(project_id));
create policy relations_delete on public.project_relations for delete to authenticated
using (private.can_edit_project(project_id));

create policy packages_read on public.project_packages for select to authenticated
using (private.can_read_project(project_id));
create policy packages_insert on public.project_packages for insert to authenticated
with check (private.can_edit_project(project_id));
create policy packages_update on public.project_packages for update to authenticated
using (private.can_edit_project(project_id)) with check (private.can_edit_project(project_id));
create policy packages_delete on public.project_packages for delete to authenticated
using (private.can_edit_project(project_id));

create policy offers_read on public.project_offers for select to authenticated
using (private.can_read_project(project_id));
create policy offers_insert on public.project_offers for insert to authenticated
with check (private.can_edit_project(project_id));

create policy budgets_read on public.project_budgets for select to authenticated
using (private.can_read_project(project_id));
create policy budgets_insert on public.project_budgets for insert to authenticated
with check (private.can_edit_project(project_id));
create policy budgets_update on public.project_budgets for update to authenticated
using (private.can_edit_project(project_id)) with check (private.can_edit_project(project_id));

create policy budget_lines_read on public.budget_lines for select to authenticated
using (private.can_read_project(project_id));
create policy budget_lines_insert on public.budget_lines for insert to authenticated
with check (private.can_edit_project(project_id));
create policy budget_lines_update on public.budget_lines for update to authenticated
using (private.can_edit_project(project_id)) with check (private.can_edit_project(project_id));
create policy budget_lines_delete on public.budget_lines for delete to authenticated
using (private.can_edit_project(project_id));

create policy snapshots_read on public.proposal_snapshots for select to authenticated
using (private.can_read_project(project_id));
create policy snapshots_insert on public.proposal_snapshots for insert to authenticated
with check (private.can_edit_project(project_id) and created_by = (select auth.uid()));
create policy audit_read on public.audit_events for select to authenticated
using (private.is_project_owner(project_id));

-- Los roles de cliente no reciben escrituras de catálogo, historial ni auditoría.
revoke all on table public.projects, public.project_memberships, public.catalog_items,
  public.project_entities, public.project_relations, public.project_packages,
  public.project_offers, public.project_budgets, public.budget_lines,
  public.proposal_snapshots, public.audit_events from public, anon, authenticated;
grant select on table public.projects, public.project_memberships, public.catalog_items,
  public.project_entities, public.project_relations, public.project_packages,
  public.project_offers, public.project_budgets, public.budget_lines,
  public.proposal_snapshots, public.audit_events to authenticated;
grant insert (owner_user_id, name) on public.projects to authenticated;
grant update (name) on public.projects to authenticated;
grant insert (project_id, user_id, role) on public.project_memberships to authenticated;
grant update (role) on public.project_memberships to authenticated;
grant delete on public.project_memberships to authenticated;
grant insert (project_id, entity_id, kind, label, origin_kind, origin_ref,
  scope_kind, scope_id, revision, knowledge_state, details) on public.project_entities to authenticated;
grant update (label, origin_ref, scope_kind, scope_id, revision, knowledge_state, details)
  on public.project_entities to authenticated;
grant delete on public.project_entities to authenticated;
grant insert (project_id, source_entity_id, predicate, target_entity_id)
  on public.project_relations to authenticated;
grant delete on public.project_relations to authenticated;
grant insert (project_id, package_id, namespace, version, subject_entity_id, facts)
  on public.project_packages to authenticated;
grant update (namespace, version, subject_entity_id, facts)
  on public.project_packages to authenticated;
grant delete on public.project_packages to authenticated;
grant insert (project_id, catalog_item_id, supplier_ref, observed_at, valid_from,
  valid_until, currency, unit_price, evidence_ref) on public.project_offers to authenticated;
grant insert (project_id, status, currency) on public.project_budgets to authenticated;
grant update (status) on public.project_budgets to authenticated;
grant insert (project_id, budget_id, entity_id, offer_id, quantity)
  on public.budget_lines to authenticated;
grant update (offer_id, quantity) on public.budget_lines to authenticated;
grant delete on public.budget_lines to authenticated;
grant insert (project_id, budget_id, revision, document) on public.proposal_snapshots to authenticated;

revoke all on function private.is_project_owner(uuid), private.can_read_project(uuid),
  private.can_edit_project(uuid), private.transfer_project_ownership(uuid, uuid),
  private.prevent_owner_membership(), private.touch_project(), private.touch_budget(),
  private.guard_entity_revision(),
  private.audit_project_change() from public, anon, authenticated;
grant execute on function private.is_project_owner(uuid), private.can_read_project(uuid),
  private.can_edit_project(uuid), private.transfer_project_ownership(uuid, uuid)
  to authenticated;

commit;
