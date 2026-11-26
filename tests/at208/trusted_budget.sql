\set ON_ERROR_STOP on
-- Comandos de servicio SQL con identidad sintética; sin JWT real.
set role at208_backend;
select private.create_project('10000000-0000-0000-0000-000000000004',
  '00000000-0000-0000-0000-000000000005','create-budget-project','Proyecto presupuesto');
do $$ declare statement_id uuid; evidence_id uuid; package_id uuid; begin
  statement_id := private.record_project_statement(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','statement-1',
    'Requirement','Requisito declarado','{}'::jsonb);
  if statement_id <> private.record_project_statement(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','statement-1',
    'Requirement','Requisito declarado','{}'::jsonb) then
    raise exception 'statement replay changed ID'; end if;
  evidence_id := private.record_project_evidence(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','evidence-1',
    '42000000-0000-0000-0000-000000000001','Fuente curada');
  if evidence_id <> private.record_project_evidence(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','evidence-1',
    '42000000-0000-0000-0000-000000000001','Fuente curada') then
    raise exception 'evidence replay changed ID'; end if;
  package_id := private.attach_project_package(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','package-1',
    'synthetic','1',statement_id::text);
  if package_id <> private.attach_project_package(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','package-1',
    'synthetic','1',statement_id::text) then
    raise exception 'package replay changed ID'; end if;
  begin
    perform private.attach_project_package(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','unknown-package',
      'unknown','1',statement_id::text);
    raise exception 'unknown package attached';
  exception when check_violation then null; end;
  begin
    perform private.record_project_statement(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','fake-rule',
      'Rule','Regla falsa','{}'::jsonb);
    raise exception 'trusted rule spoof accepted';
  exception when check_violation then null; end;
  begin
    perform private.record_project_evidence(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','fake-source',
      '42000000-0000-0000-0000-000000000099','Fuente falsa');
    raise exception 'unlisted evidence source accepted';
  exception when check_violation then null; end;
end $$;
reset role;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000005';
insert into public.project_entities
  (project_id,entity_id,kind,label,origin_kind,origin_ref,scope_kind,scope_id,revision,knowledge_state)
values
('10000000-0000-0000-0000-000000000004','req-budget','Requirement','Req',
 'user','synthetic:budget','project','req-budget',1,'known'),
('10000000-0000-0000-0000-000000000004','ev-budget','Evidence','Fuente',
 'document','synthetic:budget','project','req-budget',1,'known');
reset request.jwt.claim.sub;

set role at208_backend;
do $$ declare rate_id uuid; budget_id uuid; line_id uuid; second_id uuid;
  snapshot_id uuid; customer_id uuid; begin
  customer_id := private.record_project_customer(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','customer-1',
    'customer-private','SV','Cliente sintético reservado','private@example.invalid');
  if customer_id <> private.record_project_customer(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','customer-1',
    'customer-private','SV','Cliente sintético reservado','private@example.invalid') then
    raise exception 'customer retry changed ID'; end if;
  rate_id := private.record_project_service_rate(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','rate-1',
    '43000000-0000-0000-0000-000000000001',
    '42000000-0000-0000-0000-000000000001','ev-budget',
    date '2026-01-01',null,'USD',25);
  if rate_id <> private.record_project_service_rate(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','rate-1',
    '43000000-0000-0000-0000-000000000001',
    '42000000-0000-0000-0000-000000000001','ev-budget',
    date '2026-01-01',null,'USD',25) then
    raise exception 'service rate retry changed ID'; end if;
  budget_id := private.create_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','budget-1','USD');
  if budget_id <> private.create_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','budget-1','USD') then
    raise exception 'budget retry changed ID'; end if;
  line_id := private.add_project_budget_line(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','line-1',budget_id,1,
    'req-budget',null,rate_id,2);
  if line_id <> private.add_project_budget_line(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','line-1',budget_id,1,
    'req-budget',null,rate_id,2) then
    raise exception 'line retry changed ID'; end if;
  begin
    perform private.add_project_budget_line(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','stale-line',budget_id,1,
      'req-budget',null,rate_id,2);
    raise exception 'stale budget line accepted';
  exception when serialization_failure then null; end;
  perform private.transition_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','activate-1',budget_id,2,'active');
  if budget_id <> private.transition_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','activate-1',budget_id,2,'active') then
    raise exception 'activation retry changed ID'; end if;
  begin
    perform private.transition_project_budget(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','missing-budget-null',
      '50000000-0000-0000-0000-000000000099',null,'active');
    raise exception 'missing budget with null revision accepted';
  exception when check_violation then null; end;
  begin
    perform private.transition_project_budget(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','missing-budget-revision',
      '50000000-0000-0000-0000-000000000099',1,'active');
    raise exception 'missing budget with revision accepted';
  exception when check_violation then null; end;
  begin
    perform private.transition_project_budget(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','existing-budget-null',
      budget_id,null,'closed');
    raise exception 'null expected revision accepted';
  exception when check_violation then null; end;
  snapshot_id := private.capture_budget_draft(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','draft-1',budget_id,3);
  if snapshot_id <> private.capture_budget_draft(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','draft-1',budget_id,3) then
    raise exception 'draft retry changed ID'; end if;
  second_id := private.create_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','budget-2','USD');
  begin
    perform private.transition_project_budget(
      '10000000-0000-0000-0000-000000000004',
      '00000000-0000-0000-0000-000000000005','activate-2-too-soon',second_id,1,'active');
    raise exception 'second active budget accepted';
  exception when unique_violation then null; end;
  perform private.transition_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','close-1',budget_id,3,'closed');
  perform private.transition_project_budget(
    '10000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005','activate-2',second_id,1,'active');
end $$;
reset role;

do $$ begin
  if exists (select 1 from private.project_command_receipts
    where project_id='10000000-0000-0000-0000-000000000004'
      and command_key in ('missing-budget-null','missing-budget-revision',
                          'existing-budget-null')) then
    raise exception 'failed transition left a successful receipt';
  end if;
end $$;

do $$ begin
  if (select count(*) from public.project_service_rates where project_id =
      '10000000-0000-0000-0000-000000000004') <> 1 or
     (select count(*) from public.project_entities where project_id =
      '10000000-0000-0000-0000-000000000004') <> 4 or
     (select count(*) from public.project_packages where project_id =
      '10000000-0000-0000-0000-000000000004' and facts='{"synthetic":true}'::jsonb) <> 1 or
     (select count(*) from public.project_customers where project_id =
      '10000000-0000-0000-0000-000000000004') <> 1 or
     (select count(*) from private.customer_profiles where project_id =
      '10000000-0000-0000-0000-000000000004') <> 1 or
     (select evidence_revision from public.project_service_rates where project_id =
      '10000000-0000-0000-0000-000000000004') <> 1 or
     (select count(*) from public.budget_lines where project_id =
      '10000000-0000-0000-0000-000000000004') <> 1 or
     (select count(*) from public.proposal_snapshots where project_id =
      '10000000-0000-0000-0000-000000000004' and status='draft'
        and jsonb_array_length(document -> 'lines')=1) <> 1 or
     (select count(*) from public.project_budgets where project_id =
      '10000000-0000-0000-0000-000000000004' and status='active') <> 1 then
    raise exception 'trusted rate/budget state invalid'; end if;
end $$;
\echo AT-208 trusted rate and budget assertions passed
