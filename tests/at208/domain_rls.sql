\set ON_ERROR_STOP on
-- Fixture local: NO valida JWT. La migración fue creada por dueño NOLOGIN no superusuario.
insert into auth.users (id) values
('00000000-0000-0000-0000-000000000001'),
('00000000-0000-0000-0000-000000000002'),
('00000000-0000-0000-0000-000000000003'),
('00000000-0000-0000-0000-000000000004');
do $$ begin
  if exists (select 1 from pg_roles where rolname = 'at208_owner' and rolsuper) or
     (select pg_get_userbyid(relowner) from pg_class where oid = 'public.projects'::regclass)
       <> 'at208_owner' then raise exception 'synthetic non-superuser owner missing'; end if;
end $$;

set role at208_owner;
insert into public.catalog_items (id, namespace, version, sku, label) values
('20000000-0000-0000-0000-000000000001','synthetic','1.0.0','ITEM-1','Artículo ficticio');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.projects (id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','Proyecto A');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.projects (id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000002','Proyecto B');
insert into public.project_entities (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state)
values ('10000000-0000-0000-0000-000000000002','e-b','Requirement','Req B','user','synthetic:b','project','e-b',1,'known'),
('10000000-0000-0000-0000-000000000002','ev-b','Evidence','Fuente B','document','synthetic:b','project','e-b',1,'known');
insert into public.project_offers (project_id,id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
values ('10000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000002',
'20000000-0000-0000-0000-000000000001','supplier-b',date '2026-01-01','USD',7.25,'ev-b');

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.project_memberships (project_id,user_id,role) values
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000003','editor'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000004','viewer');
insert into public.project_entities (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state) values
('10000000-0000-0000-0000-000000000001','e-a','ProjectGoal','Meta A','user','synthetic:a','project','e-a',1,'known'),
('10000000-0000-0000-0000-000000000001','e-a2','Requirement','Req A','user','synthetic:a','project','e-a',1,'known'),
('10000000-0000-0000-0000-000000000001','ev-a','Evidence','Fuente A','document','synthetic:a','project','e-a',1,'known');
insert into public.project_relations (project_id,source_entity_id,predicate,target_entity_id)
values ('10000000-0000-0000-0000-000000000001','e-a','requires','e-a2');
insert into public.project_packages (project_id,package_id,namespace,version,subject_entity_id,facts)
values ('10000000-0000-0000-0000-000000000001','pkg-a','synthetic','1','e-a','{}');
insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
'supplier-a',date '2026-01-01','USD',10.5,'ev-a');
insert into public.project_budgets (project_id,status,currency)
values ('10000000-0000-0000-0000-000000000001','active','USD');
insert into public.budget_lines (project_id,budget_id,entity_id,offer_id,quantity)
select b.project_id,b.id,'e-a2',o.id,2 from public.project_budgets b
join public.project_offers o on o.project_id=b.project_id
where b.project_id='10000000-0000-0000-0000-000000000001';
insert into public.proposal_snapshots (project_id,budget_id,revision,document)
select project_id,id,1,'{"synthetic":true}'::jsonb from public.project_budgets;

do $$ begin
  if (select revision from public.project_budgets limit 1) <> 2 or
     (select status from public.proposal_snapshots limit 1) <> 'draft' then
    raise exception 'budget revision or draft snapshot invalid'; end if;
  begin
    insert into public.project_relations (project_id,source_entity_id,predicate,target_entity_id)
    values ('10000000-0000-0000-0000-000000000001','e-a','bad','e-b');
    raise exception 'cross tenant relation accepted';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.budget_lines (project_id,budget_id,entity_id,offer_id,quantity)
    select project_id,id,'e-a2','30000000-0000-0000-0000-000000000002',1
    from public.project_budgets limit 1;
    raise exception 'cross tenant offer accepted';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.project_budgets (project_id,status,currency)
    values ('10000000-0000-0000-0000-000000000001','active','USD');
    raise exception 'second active budget accepted';
  exception when unique_violation then null; end;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,valid_until,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'bad',date '2026-02-01',date '2026-01-01','USD',1,'synthetic:bad');
    raise exception 'invalid dates accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'bad',date '2026-01-01','USD','NaN'::numeric,'synthetic:bad');
    raise exception 'NaN price accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'bad',date '2026-01-01','USD','Infinity'::numeric,'synthetic:bad');
    raise exception 'infinite price accepted';
  exception when check_violation or numeric_value_out_of_range then null; end;
  begin
    insert into public.budget_lines (project_id,budget_id,entity_id,quantity)
    select project_id,id,'e-a2','NaN'::numeric from public.project_budgets limit 1;
    raise exception 'NaN quantity accepted';
  exception when check_violation then null; end;
  begin
    insert into public.budget_lines (project_id,budget_id,entity_id,quantity)
    select project_id,id,'e-a2','Infinity'::numeric from public.project_budgets limit 1;
    raise exception 'infinite quantity accepted';
  exception when check_violation or numeric_value_out_of_range then null; end;
end $$;
create temp table at208_revision_before as select revision from public.projects
where id='10000000-0000-0000-0000-000000000001';

reset role;
set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
do $$ begin
  if (select count(*) from public.projects) <> 1 or
     (select count(*) from public.catalog_items) <> 1 or
     (select count(*) from public.project_offers) <> 1 then
    raise exception 'authenticated read isolation failed'; end if;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'direct',date '2026-01-01','USD',1,'synthetic:direct');
    raise exception 'direct offer accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_entities (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state)
    values ('10000000-0000-0000-0000-000000000001','fake','Evidence','Fake','user','synthetic:fake','project','e-a',1,'known');
    raise exception 'direct evidence accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_packages (project_id,package_id,namespace,version,subject_entity_id,facts)
    values ('10000000-0000-0000-0000-000000000001','fake','synthetic','1','e-a','{}');
    raise exception 'direct package accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.project_entities set label='Forged', revision=2
    where project_id='10000000-0000-0000-0000-000000000001' and entity_id='ev-a';
    raise exception 'direct evidence update accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.project_offers set unit_price=1
    where project_id='10000000-0000-0000-0000-000000000001';
    raise exception 'historical offer update accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_budgets (project_id,status,currency)
    values ('10000000-0000-0000-0000-000000000001','draft','USD');
    raise exception 'direct budget accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.budget_lines (project_id,budget_id,entity_id,quantity)
    select project_id,id,'e-a2',1 from public.project_budgets limit 1;
    raise exception 'direct line accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.proposal_snapshots (project_id,budget_id,revision,document)
    select project_id,id,2,'{}'::jsonb from public.project_budgets limit 1;
    raise exception 'direct snapshot accepted';
  exception when insufficient_privilege then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      auth.uid(),'client-key','20000000-0000-0000-0000-000000000001','fake',
      date '2026-01-01',null,'USD',1,'synthetic:fake');
    raise exception 'client called service function';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.audit_events (project_id,actor_user_id,table_name,action,resource_id)
    values ('10000000-0000-0000-0000-000000000001',auth.uid(),'fake','INSERT','fake');
    raise exception 'audit forgery accepted';
  exception when insufficient_privilege then null; end;
end $$;

reset role;
set role service_role;
do $$ declare first_id uuid; retry_id uuid; begin
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'direct',date '2026-01-01','USD',1,'synthetic:direct');
    raise exception 'service role direct DML accepted';
  exception when insufficient_privilege then null; end;
  first_id := private.record_project_offer('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
    'trusted-synthetic',date '2026-01-01',null,'USD',11.5,'ev-a');
  retry_id := private.record_project_offer('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
    'trusted-synthetic',date '2026-01-01',null,'USD',11.5,'ev-a');
  if first_id <> retry_id then raise exception 'idempotent replay changed result'; end if;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'ev-a');
    raise exception 'changed idempotency payload accepted';
  exception when unique_violation then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002','foreign','20000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'ev-a');
    raise exception 'foreign actor wrote offer';
  exception when insufficient_privilege then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','no-evidence','20000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'missing-evidence');
    raise exception 'unproven offer accepted';
  exception when check_violation then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','nan-price','20000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD','NaN'::numeric,'ev-a');
    raise exception 'service accepted NaN';
  exception when check_violation then null; end;
end $$;
reset role;

set role at208_owner;
do $$ begin
  if (select revision from public.projects where id='10000000-0000-0000-0000-000000000001') <>
     (select revision+1 from at208_revision_before) or
     (select count(*) from public.project_offers where project_id='10000000-0000-0000-0000-000000000001') <> 2 then
    raise exception 'trusted offer/retry revision or count wrong'; end if;
  if not exists (select 1 from public.audit_events where table_name='project_offers'
     and actor_user_id='00000000-0000-0000-0000-000000000001'
     and project_id='10000000-0000-0000-0000-000000000001') then
    raise exception 'trusted actor audit missing'; end if;
end $$;
reset role;

set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
do $$ begin
  if (select count(*) from public.projects) <> 1 or
     (select count(*) from public.project_entities) <> 2 or
     exists (select 1 from public.project_offers where project_id='10000000-0000-0000-0000-000000000001') then
    raise exception 'B isolation failed'; end if;
  begin
    perform private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002');
    raise exception 'B transferred A';
  exception when insufficient_privilege then null; end;
end $$;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000004';
do $$ begin
  if (select count(*) from public.projects) <> 1 then raise exception 'viewer read failed'; end if;
  update public.project_memberships set role='editor'
  where project_id='10000000-0000-0000-0000-000000000001'
    and user_id='00000000-0000-0000-0000-000000000004';
  if found then raise exception 'viewer promoted self'; end if;
end $$;
reset request.jwt.claim.sub;
do $$ begin
  if (select count(*) from public.projects) <> 0 then raise exception 'null actor leaked'; end if;
end $$;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
update public.project_memberships set role='viewer'
where project_id='10000000-0000-0000-0000-000000000001'
  and user_id='00000000-0000-0000-0000-000000000003';
do $$ begin
  begin
    perform private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000003');
    raise exception 'revoked editor became owner';
  exception when check_violation then null; end;
end $$;
update public.project_memberships set role='editor'
where project_id='10000000-0000-0000-0000-000000000001'
  and user_id='00000000-0000-0000-0000-000000000003';
select private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000003');
do $$ begin
  if (select owner_user_id from public.projects where id='10000000-0000-0000-0000-000000000001') <>
     '00000000-0000-0000-0000-000000000003' then raise exception 'transfer failed'; end if;
end $$;
reset role;
reset request.jwt.claim.sub;
set role anon;
do $$ begin
  begin
    perform count(*) from public.projects;
    raise exception 'anon read accepted';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
\echo AT-208 domain, service and RLS assertions passed
