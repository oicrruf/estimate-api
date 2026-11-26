\set ON_ERROR_STOP on
-- Solo fixtures locales. Los claims se simulan en psql; esto no valida JWT.
insert into auth.users (id) values
  ('00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000002'),
  ('00000000-0000-0000-0000-000000000003'),
  ('00000000-0000-0000-0000-000000000004');
insert into public.catalog_items (id, namespace, version, sku, label) values
  ('20000000-0000-0000-0000-000000000001', 'synthetic', '1.0.0', 'ITEM-1', 'Artículo ficticio');

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.projects (id, owner_user_id, name) values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Proyecto A');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.projects (id, owner_user_id, name) values
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'Proyecto B');
insert into public.project_entities
  (project_id, entity_id, kind, label, origin_kind, origin_ref, scope_kind, scope_id,
   revision, knowledge_state) values
  ('10000000-0000-0000-0000-000000000002', 'e-b', 'Requirement', 'Req B',
   'user', 'synthetic:b', 'project', 'e-b', 1, 'known');
insert into public.project_offers
  (project_id, id, catalog_item_id, supplier_ref, valid_from, currency, unit_price, evidence_ref)
  values ('10000000-0000-0000-0000-000000000002',
          '30000000-0000-0000-0000-000000000002',
          '20000000-0000-0000-0000-000000000001',
          'supplier-b', date '2026-01-01', 'USD', 7.2500, 'synthetic:b');
reset request.jwt.claim.sub;

set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
do $$ begin
  if (select count(*) from public.projects) <> 1 then raise exception 'A project isolation failed'; end if;
  if (select count(*) from public.catalog_items) <> 1 then raise exception 'catalog read failed'; end if;
  if (select count(*) from public.project_offers) <> 0 then raise exception 'offer leak'; end if;
end $$;

insert into public.project_memberships (project_id, user_id, role) values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', 'editor');
insert into public.project_memberships (project_id, user_id, role) values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000004', 'viewer');
insert into public.project_entities
  (project_id, entity_id, kind, label, origin_kind, origin_ref, scope_kind, scope_id,
   revision, knowledge_state) values
  ('10000000-0000-0000-0000-000000000001', 'e-a', 'ProjectGoal', 'Meta A',
   'user', 'synthetic:a', 'project', 'e-a', 1, 'known'),
  ('10000000-0000-0000-0000-000000000001', 'e-a2', 'Requirement', 'Req A',
   'user', 'synthetic:a', 'project', 'e-a', 1, 'known');
insert into public.project_relations (project_id, source_entity_id, predicate, target_entity_id)
values ('10000000-0000-0000-0000-000000000001', 'e-a', 'requires', 'e-a2');
insert into public.project_packages
  (project_id, package_id, namespace, version, subject_entity_id, facts)
values ('10000000-0000-0000-0000-000000000001', 'pkg-a', 'synthetic', '1.0.0', 'e-a', '{}');
insert into public.project_offers
  (project_id, catalog_item_id, supplier_ref, valid_from, currency, unit_price, evidence_ref)
values ('10000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001', 'supplier-a', date '2026-01-01',
        'USD', 10.5000, 'synthetic:a');
insert into public.project_budgets (project_id, status, currency)
values ('10000000-0000-0000-0000-000000000001', 'active', 'USD');
insert into public.budget_lines (project_id, budget_id, entity_id, offer_id, quantity)
select '10000000-0000-0000-0000-000000000001', b.id, 'e-a2', o.id, 2
from public.project_budgets b join public.project_offers o on o.project_id = b.project_id
where b.project_id = '10000000-0000-0000-0000-000000000001';
insert into public.proposal_snapshots (project_id, budget_id, revision, document)
select b.project_id, b.id, 1, '{"synthetic":true}'::jsonb
from public.project_budgets b
where b.project_id = '10000000-0000-0000-0000-000000000001';

do $$ begin
  if (select count(*) from public.audit_events
      where project_id = '10000000-0000-0000-0000-000000000001'
        and actor_user_id = '00000000-0000-0000-0000-000000000001') < 8 then
    raise exception 'audit missing';
  end if;
  if exists (select 1 from public.audit_events where resource_id like '%synthetic:%') then
    raise exception 'audit copied source payload';
  end if;
  begin
    insert into public.project_relations (project_id, source_entity_id, predicate, target_entity_id)
    values ('10000000-0000-0000-0000-000000000001', 'e-a', 'invalid', 'e-b');
    raise exception 'cross-project relation accepted';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.budget_lines (project_id, budget_id, entity_id, offer_id, quantity)
    select b.project_id, b.id, 'e-a2', '30000000-0000-0000-0000-000000000002', 1
    from public.project_budgets b where b.project_id = '10000000-0000-0000-0000-000000000001';
    raise exception 'cross-project offer accepted';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.project_budgets (project_id, status, currency)
    values ('10000000-0000-0000-0000-000000000001', 'active', 'USD');
    raise exception 'second active budget accepted';
  exception when unique_violation then null; end;
  begin
    insert into public.project_offers
      (project_id, catalog_item_id, supplier_ref, valid_from, valid_until,
       currency, unit_price, evidence_ref)
    values ('10000000-0000-0000-0000-000000000001',
            '20000000-0000-0000-0000-000000000001', 'invalid',
            date '2026-02-01', date '2026-01-01', 'USD', 1, 'synthetic:invalid');
    raise exception 'invalid offer dates accepted';
  exception when check_violation then null; end;
  begin
    update public.projects set owner_user_id = '00000000-0000-0000-0000-000000000002'
    where id = '10000000-0000-0000-0000-000000000001';
    raise exception 'direct owner update accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_memberships (project_id, user_id, role)
    values ('10000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000001', 'editor');
    raise exception 'owner membership accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_memberships (project_id, user_id, role)
    values ('10000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000004', 'viewer');
    raise exception 'duplicate membership accepted';
  exception when unique_violation then null; end;
  begin
    update public.project_entities set revision = 3
    where project_id = '10000000-0000-0000-0000-000000000001' and entity_id = 'e-a';
    raise exception 'nonsequential revision accepted';
  exception when check_violation then null; end;
  begin
    insert into public.catalog_items (namespace, version, sku, label)
    values ('synthetic', '1.0.0', 'unauthorized', 'Invalid');
    raise exception 'catalog write accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.project_offers set unit_price = 1
    where project_id = '10000000-0000-0000-0000-000000000001';
    raise exception 'historical offer update accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.proposal_snapshots set document = '{}'::jsonb
    where project_id = '10000000-0000-0000-0000-000000000001';
    raise exception 'snapshot update accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.audit_events (project_id, actor_user_id, table_name, action, resource_id)
    values ('10000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000001', 'fake', 'INSERT', 'fake');
    raise exception 'audit forgery accepted';
  exception when insufficient_privilege then null; end;
end $$;

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
do $$ begin
  if (select count(*) from public.projects) <> 1 then raise exception 'B project isolation failed'; end if;
  if (select count(*) from public.project_entities) <> 1 then raise exception 'B entity isolation failed'; end if;
  if (select count(*) from public.audit_events) <> 3 then raise exception 'B audit isolation failed'; end if;
  begin
    insert into public.project_entities
      (project_id, entity_id, kind, label, origin_kind, origin_ref, scope_kind,
       scope_id, revision, knowledge_state)
    values ('10000000-0000-0000-0000-000000000001', 'injection', 'Requirement',
            'Invalid', 'user', 'synthetic:b', 'project', 'e-a', 1, 'known');
    raise exception 'B wrote project A';
  exception when insufficient_privilege then null; end;
  begin
    perform private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
                                                '00000000-0000-0000-0000-000000000002');
    raise exception 'B transferred project A';
  exception when insufficient_privilege then null; end;
end $$;

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000004';
do $$ begin
  if (select count(*) from public.projects) <> 1 then raise exception 'viewer cannot read project'; end if;
  if (select count(*) from public.project_entities) <> 2 then raise exception 'viewer cannot read entities'; end if;
  begin
    update public.project_entities set label = 'Invalid', revision = 2
    where project_id = '10000000-0000-0000-0000-000000000001' and entity_id = 'e-a';
    if found then raise exception 'viewer updated entity'; end if;
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_memberships (project_id, user_id, role)
    values ('10000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000002', 'editor');
    raise exception 'viewer added member';
  exception when insufficient_privilege then null; end;
end $$;

reset request.jwt.claim.sub;
do $$ begin
  if (select count(*) from public.projects) <> 0 then raise exception 'missing identity leaked projects'; end if;
  begin
    insert into public.projects (owner_user_id, name)
    values ('00000000-0000-0000-0000-000000000001', 'No actor');
    raise exception 'project created without identity';
  exception when insufficient_privilege then null; end;
end $$;

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
select private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
                                          '00000000-0000-0000-0000-000000000003');
do $$ begin
  if (select owner_user_id from public.projects
      where id = '10000000-0000-0000-0000-000000000001')
      <> '00000000-0000-0000-0000-000000000003' then
    raise exception 'new owner not set';
  end if;
  if (select role from public.project_memberships
      where project_id = '10000000-0000-0000-0000-000000000001'
        and user_id = '00000000-0000-0000-0000-000000000001') <> 'editor' then
    raise exception 'old owner not editor';
  end if;
end $$;
reset role;
reset request.jwt.claim.sub;
set role anon;
do $$ begin
  begin
    perform count(*) from public.projects;
    raise exception 'anonymous read accepted';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
\echo AT-208 domain and RLS assertions passed
