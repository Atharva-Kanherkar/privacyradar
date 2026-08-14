-- Per-source fetch jobs, expiring leases, operator audit, and extended
-- safe error codes. Additive. Does not rewrite 0001 or 0002 checksums.

alter table policy_sources
  add column if not exists due_at timestamptz,
  add column if not exists lease_owner text,
  add column if not exists lease_token uuid,
  add column if not exists lease_expires_at timestamptz,
  add column if not exists retry_count integer not null default 0,
  add column if not exists etag text,
  add column if not exists last_modified text,
  add column if not exists quarantine_reason text,
  add column if not exists quarantined_at timestamptz;

update policy_sources
set due_at = coalesce(last_success_at + interval '6 hours', now())
where due_at is null;

alter table policy_sources
  alter column due_at set default now();

alter table policy_sources
  alter column due_at set not null;

alter table policy_sources drop constraint if exists policy_sources_quarantine_reason_check;
alter table policy_sources
  add constraint policy_sources_quarantine_reason_check
  check (
    quarantine_reason is null
    or quarantine_reason in (
      'consecutive_failures', 'invalid_content', 'blocked', 'ssrf',
      'robots', 'moved', 'oversize', 'poison'
    )
  );

alter table policy_sources drop constraint if exists policy_sources_last_failure_code_check;
alter table policy_sources
  add constraint policy_sources_last_failure_code_check
  check (
    last_failure_code is null
    or last_failure_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx', 'http_429',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network',
      'blocked', 'robots', 'ssrf', 'oversize', 'moved'
    )
  );

create index if not exists policy_sources_claim_idx
  on policy_sources (due_at)
  where enabled and health_status <> 'quarantined';

create index if not exists policy_sources_lease_idx
  on policy_sources (lease_expires_at)
  where lease_expires_at is not null;

do $$
declare
  r record;
begin
  for r in
    select conname
    from pg_constraint
    where conrelid = 'source_attempts'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) like '%error_code%'
  loop
    execute format('alter table source_attempts drop constraint %I', r.conname);
  end loop;
end
$$;

alter table source_attempts drop constraint if exists source_attempts_error_code_check;
alter table source_attempts
  add constraint source_attempts_error_code_check
  check (
    error_code is null
    or error_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx', 'http_429',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network',
      'blocked', 'robots', 'ssrf', 'oversize', 'moved'
    )
  );

create table if not exists fetch_jobs (
  id                uuid primary key default gen_random_uuid(),
  idempotency_key   text not null unique,
  source_id         uuid not null references policy_sources(id) on delete cascade,
  status            text not null,
  attempt_no        integer not null default 0,
  lease_owner       text,
  lease_token       uuid,
  lease_expires_at  timestamptz,
  run_after         timestamptz not null default now(),
  finished_at       timestamptz,
  error_code        text,
  created_at        timestamptz not null default now(),
  check (
    status in (
      'pending', 'leased', 'succeeded', 'retryable_failed',
      'quarantined', 'cancelled'
    )
  ),
  check (
    error_code is null
    or error_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx', 'http_429',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network',
      'blocked', 'robots', 'ssrf', 'oversize', 'moved'
    )
  )
);

create index if not exists fetch_jobs_status_run_after_idx
  on fetch_jobs (status, run_after);

create index if not exists fetch_jobs_source_created_idx
  on fetch_jobs (source_id, created_at desc);

create table if not exists source_operator_actions (
  id          uuid primary key default gen_random_uuid(),
  source_id   uuid not null references policy_sources(id) on delete cascade,
  action      text not null,
  actor       text not null,
  reason      text,
  created_at  timestamptz not null default now(),
  metadata    jsonb not null default '{}'::jsonb,
  check (action in ('retry', 'disable', 'enable')),
  check (actor ~ '^[a-z0-9][a-z0-9:_-]{1,62}$'),
  check (
    reason is null
    or (
      char_length(reason) <= 64
      and reason !~ '@'
      and reason !~ '://'
    )
  )
);

create index if not exists source_operator_actions_source_created_idx
  on source_operator_actions (source_id, created_at desc);
