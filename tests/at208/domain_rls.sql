\set ON_ERROR_STOP on
-- Fixture local: NO valida JWT. La migración fue creada por dueño NOLOGIN no superusuario.
insert into auth.users (id) values
('00000000-0000-0000-0000-000000000001'),
('00000000-0000-0000-0000-000000000002'),
('00000000-0000-0000-0000-000000000003'),
('00000000-0000-0000-0000-000000000004'),
('00000000-0000-0000-0000-000000000005');
do $$ begin
  if exists (select 1 from pg_roles where rolname in
      ('at208_owner','at208_policy_owner','at208_mutation_owner',
       'at208_audit_owner','at208_backend') and (rolsuper or rolbypassrls)) or
     (select pg_get_userbyid(relowner) from pg_class where oid = 'public.projects'::regclass)
       <> 'at208_owner' then raise exception 'synthetic non-superuser owner missing'; end if;
  if exists (select 1 from pg_roles where rolname = 'at208_backend' and
             (rolsuper or rolbypassrls)) then
    raise exception 'backend role is privileged'; end if;
  if has_table_privilege('at208_backend','public.projects','INSERT') or
     has_table_privilege('at208_backend','public.project_offers','INSERT') or
     has_table_privilege('authenticated','public.project_memberships','UPDATE') then
    raise exception 'direct client/backend DML grant leaked'; end if;
  if (select pg_get_userbyid(proowner) from pg_proc
      where oid = 'private.can_read_project(uuid)'::regprocedure)
      <> 'at208_policy_owner' or
     (select pg_get_userbyid(proowner) from pg_proc
      where oid = 'private.record_project_offer(uuid,uuid,text,uuid,uuid,uuid,uuid,text,date,date,text,numeric,text)'::regprocedure)
      <> 'at208_mutation_owner' or
     (select pg_get_userbyid(proowner) from pg_proc
      where oid = 'private.audit_project_change()'::regprocedure)
      <> 'at208_audit_owner' or
     has_table_privilege('at208_policy_owner','public.projects','UPDATE') or
     (select rolbypassrls from pg_roles where rolname='at208_policy_owner') then
    raise exception 'RLS helper owner is too privileged'; end if;
  if exists (select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
             where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity) then
    raise exception 'public table without RLS'; end if;
end $$;

-- Las semillas se insertan con postgres local; las funciones se prueban con
-- propietarios NOLOGIN NOBYPASS y el backend sin DML directo.
insert into public.catalog_items (id, namespace, version, brand, model, sku, label) values
('20000000-0000-0000-0000-000000000001','synthetic','1.0.0',
 'Marca ficticia','Modelo uno','ITEM-1','Artículo ficticio'),
('20000000-0000-0000-0000-000000000002','synthetic','1.0.0',
 'Marca ficticia','Modelo dos','ITEM-2','Alternativa ficticia');
do $$ begin
  begin
    insert into public.catalog_items (namespace,version,brand,model,sku,label)
    values ('other','2','MARCA FICTICIA','Modelo uno','item-1','Duplicado');
    raise exception 'product identity duplicate accepted';
  exception when unique_violation then null; end;
end $$;
insert into public.countries (code,name) values ('SV','El Salvador');
insert into public.suppliers (id,country_code,display_name,registry_ref) values
('40000000-0000-0000-0000-000000000001','SV','Proveedor ficticio','synthetic-supplier'),
('40000000-0000-0000-0000-000000000002','SV','Otro proveedor','synthetic-other');
insert into public.supplier_branches (id,supplier_id,country_code,branch_ref,label) values
('41000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001',
 'SV','branch-1','Sucursal ficticia'),
('41000000-0000-0000-0000-000000000002','40000000-0000-0000-0000-000000000002',
 'SV','branch-2','Otra sucursal');
insert into public.research_sources (id,source_ref,title,observed_at) values
('42000000-0000-0000-0000-000000000001','synthetic-source','Fuente ficticia',now());
insert into public.knowledge_package_versions (namespace,version,source_id,facts) values
('synthetic','1','42000000-0000-0000-0000-000000000001','{"synthetic":true}'::jsonb),
('synthetic','1.0.0','42000000-0000-0000-0000-000000000001','{}'::jsonb);
insert into public.product_equivalences (left_item_id,right_item_id,source_id,relation) values
('20000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002',
 '42000000-0000-0000-0000-000000000001','compatible_alternative');
insert into public.product_specs (catalog_item_id,spec_key,value_text,source_id) values
('20000000-0000-0000-0000-000000000001','material','ficticio',
 '42000000-0000-0000-0000-000000000001');
insert into public.product_warranties (catalog_item_id,source_id,months,terms_ref) values
('20000000-0000-0000-0000-000000000001','42000000-0000-0000-0000-000000000001',12,'synthetic-terms');
insert into public.service_definitions (id,code,label) values
('43000000-0000-0000-0000-000000000001','synthetic-service','Servicio ficticio');
insert into private.supplier_contacts (branch_id,name,email) values
('41000000-0000-0000-0000-000000000001','Contacto privado','contact@example.invalid');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.projects (id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','Proyecto A');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.projects (id,owner_user_id,name) values
('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000002','Proyecto B');
insert into public.project_entities (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state)
values ('10000000-0000-0000-0000-000000000002','e-b','Requirement','Req B','user','synthetic:b','project','e-b',1,'known'),
('10000000-0000-0000-0000-000000000002','ev-b','Evidence','Fuente B','document','synthetic:b','project','e-b',1,'known');
insert into public.project_offers (project_id,id,catalog_item_id,supplier_id,supplier_branch_id,source_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
values ('10000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000002',
'20000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001',
'41000000-0000-0000-0000-000000000001','42000000-0000-0000-0000-000000000001',
'supplier-b',date '2026-01-01','USD',7.25,'ev-b');

set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.project_memberships (project_id,user_id,role) values
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000003','editor'),
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000004','viewer');
insert into public.project_entities (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state) values
('10000000-0000-0000-0000-000000000001','e-a','ProjectGoal','Meta A','user','synthetic:a','project','e-a',1,'known'),
('10000000-0000-0000-0000-000000000001','e-a2','Requirement','Req A','user','synthetic:a','project','e-a',1,'known'),
('10000000-0000-0000-0000-000000000001','e-a3','Requirement','Req futura','user','synthetic:a','project','e-a',1,'known'),
('10000000-0000-0000-0000-000000000001','ev-a','Evidence','Fuente A','document','synthetic:a','project','e-a',1,'known');
insert into public.project_relations (project_id,source_entity_id,predicate,target_entity_id)
values ('10000000-0000-0000-0000-000000000001','e-a','requires','e-a2');
insert into public.project_packages (project_id,package_id,namespace,version,subject_entity_id,facts)
values ('10000000-0000-0000-0000-000000000001','pkg-a','synthetic','1','e-a','{}');
insert into public.project_offers (project_id,catalog_item_id,supplier_id,supplier_branch_id,source_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
'40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
'42000000-0000-0000-0000-000000000001','supplier-a',date '2026-01-01','USD',10.5,'ev-a');
insert into public.project_budgets (project_id,status,currency)
values ('10000000-0000-0000-0000-000000000001','active','USD');
insert into public.budget_lines (project_id,budget_id,entity_id,offer_id,quantity)
select b.project_id,b.id,'e-a2',o.id,2 from public.project_budgets b
join public.project_offers o on o.project_id=b.project_id
where b.project_id='10000000-0000-0000-0000-000000000001';
insert into public.proposal_snapshots (project_id,budget_id,revision,document)
select project_id,id,1,'{"synthetic":true}'::jsonb from public.project_budgets;
insert into public.project_customers (project_id,id,customer_ref,country_code) values
('10000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','customer-a','SV');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.project_customers (project_id,id,customer_ref,country_code) values
('10000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000002','customer-b','SV');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into private.customer_profiles (project_id,customer_id,legal_name,contact_email) values
('10000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001',
 'Cliente privado A','private-a@example.invalid');
insert into public.project_candidates (project_id,requirement_entity_id,catalog_item_id,status,evidence_ref) values
('10000000-0000-0000-0000-000000000001','e-a2','20000000-0000-0000-0000-000000000001','selected','ev-a');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.project_candidates (project_id,requirement_entity_id,catalog_item_id,status,evidence_ref) values
('10000000-0000-0000-0000-000000000002','e-b','20000000-0000-0000-0000-000000000001','rejected','ev-b');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.project_evaluations
  (project_id,id,requirement_entity_id,catalog_item_id,evidence_ref,outcome,rationale) values
('10000000-0000-0000-0000-000000000001','51000000-0000-0000-0000-000000000001','e-a2',
 '20000000-0000-0000-0000-000000000001','ev-a','accepted','Evaluación ficticia');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
insert into public.project_evaluations
  (project_id,id,requirement_entity_id,catalog_item_id,evidence_ref,outcome,rationale) values
('10000000-0000-0000-0000-000000000002','51000000-0000-0000-0000-000000000002','e-b',
 '20000000-0000-0000-0000-000000000001','ev-b','rejected','Evaluación ficticia');
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
insert into public.project_selections (project_id,requirement_entity_id,catalog_item_id,evaluation_id)
values ('10000000-0000-0000-0000-000000000001','e-a2','20000000-0000-0000-0000-000000000001',
        '51000000-0000-0000-0000-000000000001');
insert into public.project_service_rates
  (project_id,service_id,source_id,evidence_ref,valid_from,currency,observed_amount)
values ('10000000-0000-0000-0000-000000000001','43000000-0000-0000-0000-000000000001',
        '42000000-0000-0000-0000-000000000001','ev-a',date '2026-01-01','USD',25.0);

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
    insert into public.project_selections (project_id,requirement_entity_id,catalog_item_id,evaluation_id)
    values ('10000000-0000-0000-0000-000000000001','e-a',
            '20000000-0000-0000-0000-000000000001','51000000-0000-0000-0000-000000000002');
    raise exception 'foreign evaluation selected';
  exception when foreign_key_violation then null; end;
  begin
    insert into public.project_service_rates
      (project_id,service_id,source_id,evidence_ref,valid_from,currency,observed_amount)
    values ('10000000-0000-0000-0000-000000000001',
            '43000000-0000-0000-0000-000000000001',
            '42000000-0000-0000-0000-000000000001','ev-a',
            date '2026-01-01','USD','NaN'::numeric);
    raise exception 'NaN service rate accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_offers
      (project_id,catalog_item_id,supplier_id,supplier_branch_id,source_id,supplier_ref,
       valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000002',
            '42000000-0000-0000-0000-000000000001','bad',date '2026-01-01','USD',1,'ev-a');
    raise exception 'supplier branch mismatch accepted';
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
    insert into public.project_offers (project_id,catalog_item_id,supplier_id,source_id,supplier_ref,valid_from,valid_until,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            '40000000-0000-0000-0000-000000000001','42000000-0000-0000-0000-000000000001',
            'bad',date '2026-02-01',date '2026-01-01','USD',1,'synthetic:bad');
    raise exception 'invalid dates accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_id,source_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            '40000000-0000-0000-0000-000000000001','42000000-0000-0000-0000-000000000001',
            'bad',date '2026-01-01','USD','NaN'::numeric,'synthetic:bad');
    raise exception 'NaN price accepted';
  exception when check_violation then null; end;
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_id,source_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            '40000000-0000-0000-0000-000000000001','42000000-0000-0000-0000-000000000001',
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
     (select count(*) from public.catalog_items) <> 2 or
     (select count(*) from public.project_offers) <> 1 or
     (select count(*) from public.product_specs) <> 1 or
     (select count(*) from public.project_customers) <> 1 or
     (select count(*) from public.project_candidates) <> 1 or
     (select count(*) from public.project_service_rates) <> 1 then
    raise exception 'authenticated read isolation failed'; end if;
  begin
    perform count(*) from private.supplier_contacts;
    raise exception 'private supplier contact exposed';
  exception when insufficient_privilege then null; end;
  begin
    perform count(*) from private.customer_profiles;
    raise exception 'private customer contact exposed';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_candidates (project_id,requirement_entity_id,catalog_item_id,status,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','e-a',
            '20000000-0000-0000-0000-000000000001','selected','ev-a');
    raise exception 'direct selection candidate accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.projects (owner_user_id,name)
    values (auth.uid(),'Direct project');
    raise exception 'direct project creation accepted';
  exception when insufficient_privilege then null; end;
  begin
    update public.projects set name='Direct rename'
    where id='10000000-0000-0000-0000-000000000001';
    raise exception 'direct project update accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_memberships (project_id,user_id,role)
    values ('10000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000002','viewer');
    raise exception 'direct membership accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_evaluations
      (project_id,requirement_entity_id,catalog_item_id,evidence_ref,outcome,rationale)
    values ('10000000-0000-0000-0000-000000000001','e-a2',
            '20000000-0000-0000-0000-000000000001','ev-a','accepted','forged');
    raise exception 'direct evaluation accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_selections
      (project_id,requirement_entity_id,catalog_item_id,evaluation_id)
    values ('10000000-0000-0000-0000-000000000001','e-a2',
            '20000000-0000-0000-0000-000000000001',
            '51000000-0000-0000-0000-000000000001');
    raise exception 'direct selection accepted';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.project_service_rates
      (project_id,service_id,source_id,evidence_ref,valid_from,currency,observed_amount)
    values ('10000000-0000-0000-0000-000000000001',
            '43000000-0000-0000-0000-000000000001',
            '42000000-0000-0000-0000-000000000001','ev-a',
            date '2026-01-01','USD',1);
    raise exception 'direct service rate accepted';
  exception when insufficient_privilege then null; end;
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
      auth.uid(),'client-key','20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001','fake',
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
do $$ begin
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','service-key',
      '20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001','fake',date '2026-01-01',null,
      'USD',1,'ev-a');
    raise exception 'service_role called private SQL procedure';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
set role at208_backend;
do $$ declare first_id uuid; retry_id uuid; begin
  begin
    insert into public.project_offers (project_id,catalog_item_id,supplier_ref,valid_from,currency,unit_price,evidence_ref)
    values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',
            'direct',date '2026-01-01','USD',1,'synthetic:direct');
    raise exception 'service role direct DML accepted';
  exception when insufficient_privilege then null; end;
  first_id := private.record_project_offer('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
    '42000000-0000-0000-0000-000000000001',
    'trusted-synthetic',date '2026-01-01',null,'USD',11.5,'ev-a');
  retry_id := private.record_project_offer('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
    '42000000-0000-0000-0000-000000000001',
    'trusted-synthetic',date '2026-01-01',null,'USD',11.5,'ev-a');
  if first_id <> retry_id then raise exception 'idempotent replay changed result'; end if;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'ev-a');
    raise exception 'changed idempotency payload accepted';
  exception when unique_violation then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002','foreign','20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'ev-a');
    raise exception 'foreign actor wrote offer';
  exception when insufficient_privilege then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','no-evidence','20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD',12,'missing-evidence');
    raise exception 'unproven offer accepted';
  exception when check_violation then null; end;
  begin
    perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','nan-price','20000000-0000-0000-0000-000000000001',
      '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
      '42000000-0000-0000-0000-000000000001',
      'trusted-synthetic',date '2026-01-01',null,'USD','NaN'::numeric,'ev-a');
    raise exception 'service accepted NaN';
  exception when check_violation then null; end;
end $$;
reset role;

-- Comprobación administrativa de resultados; no representa una ruta de app.
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
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000001';
-- Simula una revisión posterior de evidencia mediante administración local;
-- una oferta histórica debe conservar el contenido y revisión originales.
update public.project_entities set revision=2, details='{"revised":true}'::jsonb
where project_id='10000000-0000-0000-0000-000000000001' and entity_id='ev-a';
reset request.jwt.claim.sub;
do $$ begin
  if (select evidence_revision from public.project_offers
      where project_id='10000000-0000-0000-0000-000000000001'
        and supplier_ref='trusted-synthetic') <> 1 or
     (select evidence_snapshot ->> 'revision' from public.project_offers
      where project_id='10000000-0000-0000-0000-000000000001'
        and supplier_ref='trusted-synthetic') <> '1' then
    raise exception 'historical offer evidence changed'; end if;
end $$;
reset role;

set role at208_backend;
do $$ declare candidate_id uuid; evaluation_id uuid; selected_id uuid; begin
  perform private.record_project_offer('10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','offer-1','20000000-0000-0000-0000-000000000001',
    '40000000-0000-0000-0000-000000000001','41000000-0000-0000-0000-000000000001',
    '42000000-0000-0000-0000-000000000001',
    'trusted-synthetic',date '2026-01-01',null,'USD',11.5,'ev-a');
  candidate_id := private.record_project_candidate(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','candidate-2','e-a3',
    '20000000-0000-0000-0000-000000000002','ev-a');
  if candidate_id <> private.record_project_candidate(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','candidate-2','e-a3',
    '20000000-0000-0000-0000-000000000002','ev-a') then
    raise exception 'candidate replay changed result'; end if;
  evaluation_id := private.record_project_evaluation(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','evaluation-2','e-a3',
    '20000000-0000-0000-0000-000000000002','ev-a','accepted','Evaluación comprobada');
  if evaluation_id <> private.record_project_evaluation(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','evaluation-2','e-a3',
    '20000000-0000-0000-0000-000000000002','ev-a','accepted','Evaluación comprobada') then
    raise exception 'evaluation replay changed result'; end if;
  selected_id := private.select_project_candidate(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','selection-2','e-a3',
    '20000000-0000-0000-0000-000000000002',evaluation_id);
  if selected_id <> private.select_project_candidate(
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001','selection-2','e-a3',
    '20000000-0000-0000-0000-000000000002',evaluation_id) then
    raise exception 'selection replay changed result'; end if;
  begin
    perform private.record_project_candidate(
      '10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002','foreign-candidate','e-a3',
      '20000000-0000-0000-0000-000000000001','ev-a');
    raise exception 'foreign actor recorded candidate';
  exception when insufficient_privilege then null; end;
  begin
    perform private.record_project_evaluation(
      '10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','bad-evaluation','e-a3',
      '20000000-0000-0000-0000-000000000002','missing','accepted','Sin evidencia');
    raise exception 'unproven evaluation accepted';
  exception when check_violation then null; end;
end $$;
reset role;
-- Comprobación administrativa de resultados; no representa una ruta de app.
do $$ begin
  if (select count(*) from public.project_selections
      where project_id='10000000-0000-0000-0000-000000000001') <> 2 or
     (select count(*) from public.project_evaluations
      where project_id='10000000-0000-0000-0000-000000000001') <> 2 then
    raise exception 'trusted candidate/evaluation/selection missing or duplicated'; end if;
end $$;
reset role;

set role at208_backend;
do $$ declare created uuid; member uuid; begin
  created := private.create_project('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005','create-c','Proyecto C');
  if created <> private.create_project('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005','create-c','Proyecto C') then
    raise exception 'project create replay failed'; end if;
  member := private.set_project_member('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005','member-add',
    '00000000-0000-0000-0000-000000000003','viewer');
  if member <> private.set_project_member('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005','member-add',
    '00000000-0000-0000-0000-000000000003','viewer') then
    raise exception 'membership replay failed'; end if;
  perform private.set_project_member('10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005','member-remove',
    '00000000-0000-0000-0000-000000000003',null);
  begin
    perform private.set_project_member('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002','foreign-member',
      '00000000-0000-0000-0000-000000000005','editor');
    raise exception 'non-owner managed membership';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
do $$ begin
  if (select count(*) from public.projects where id='10000000-0000-0000-0000-000000000003') <> 1 or
     exists (select 1 from public.project_memberships
             where project_id='10000000-0000-0000-0000-000000000003') then
    raise exception 'project/member command result wrong'; end if;
end $$;

set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000002';
do $$ begin
  if (select count(*) from public.projects) <> 1 or
     (select count(*) from public.project_entities) <> 2 or
     (select count(*) from public.project_candidates) <> 1 or
     (select count(*) from public.project_customers) <> 1 or
     exists (select 1 from public.project_offers where project_id='10000000-0000-0000-0000-000000000001') then
    raise exception 'B isolation failed'; end if;
  begin
    perform private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000002','direct',
      '00000000-0000-0000-0000-000000000003');
    raise exception 'client called transfer';
  exception when insufficient_privilege then null; end;
end $$;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000004';
do $$ begin
  if (select count(*) from public.projects) <> 1 then raise exception 'viewer read failed'; end if;
  begin
    update public.project_memberships set role='editor'
    where project_id='10000000-0000-0000-0000-000000000001'
      and user_id='00000000-0000-0000-0000-000000000004';
    raise exception 'viewer promoted self';
  exception when insufficient_privilege then null; end;
end $$;
reset request.jwt.claim.sub;
do $$ begin
  if (select count(*) from public.projects) <> 0 then raise exception 'null actor leaked'; end if;
end $$;
reset role;
set role at208_backend;
select private.set_project_member('10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001','downgrade-editor',
  '00000000-0000-0000-0000-000000000003','viewer');
do $$ begin
  begin
    perform private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
      '00000000-0000-0000-0000-000000000001','invalid-transfer',
      '00000000-0000-0000-0000-000000000003');
    raise exception 'revoked editor became owner';
  exception when check_violation then null; end;
end $$;
select private.set_project_member('10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001','restore-editor',
  '00000000-0000-0000-0000-000000000003','editor');
select private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001','transfer-a-to-c',
  '00000000-0000-0000-0000-000000000003');
select private.transfer_project_ownership('10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001','transfer-a-to-c',
  '00000000-0000-0000-0000-000000000003');
reset role;
set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000003';
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
