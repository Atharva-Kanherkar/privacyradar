-- Current-head schema reference. Apply with `privacyradar migrate`.
-- Docker-compose may bootstrap from this file; migrate still records 0001–0003
-- and installs append-only triggers. This file matches the end state of
-- db/migrations/0001_initial.sql plus 0002 and 0003 DDL (without DML/triggers).

create extension if not exists pgcrypto;

create table if not exists companies (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  name          text not null,
  website       text not null,
  category      text not null default 'consumer',
  created_at    timestamptz not null default now()
);

create table if not exists policy_sources (
  id                      uuid primary key default gen_random_uuid(),
  company_id              uuid not null references companies(id) on delete cascade,
  kind                    text not null default 'privacy',
  url                     text not null,
  region                  text not null default 'global',
  enabled                 boolean not null default true,
  crawl_delay_s           integer not null default 2,
  current_snapshot_id     uuid,
  current_observation_id  uuid,
  health_status           text not null default 'pending',
  last_attempt_at         timestamptz,
  last_success_at         timestamptz,
  last_failure_code       text,
  consecutive_failures    integer not null default 0,
  due_at                  timestamptz not null default now(),
  lease_owner             text,
  lease_token             uuid,
  lease_expires_at        timestamptz,
  retry_count             integer not null default 0,
  etag                    text,
  last_modified           text,
  quarantine_reason       text,
  quarantined_at          timestamptz,
  unique (company_id, kind, region),
  check (health_status in ('pending', 'healthy', 'degraded', 'quarantined')),
  check (
    last_failure_code is null
    or last_failure_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx', 'http_429',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network',
      'blocked', 'robots', 'ssrf', 'oversize', 'moved'
    )
  ),
  check (
    quarantine_reason is null
    or quarantine_reason in (
      'consecutive_failures', 'invalid_content', 'blocked', 'ssrf',
      'robots', 'moved', 'oversize', 'poison'
    )
  )
);

create index if not exists policy_sources_claim_idx
  on policy_sources (due_at)
  where enabled and health_status <> 'quarantined';

create index if not exists policy_sources_lease_idx
  on policy_sources (lease_expires_at)
  where lease_expires_at is not null;

create table if not exists snapshots (
  id                  uuid primary key default gen_random_uuid(),
  source_id           uuid not null references policy_sources(id) on delete cascade,
  fetched_at          timestamptz not null default now(),
  http_status         integer,
  content_type        text,
  raw_html            text,
  markdown            text,
  doc_hash            text not null,
  section_hashes      jsonb not null default '{}'::jsonb,
  fetch_error         text,
  final_url           text,
  language            text,
  region              text not null default 'global',
  strategy            text not null default 'http',
  byte_count          integer,
  raw_sha256          text,
  normalized_sha256   text,
  normalizer_version  text not null default '1.0.0',
  is_valid            boolean not null default true,
  constraint snapshots_source_hash_normalizer_key
    unique (source_id, doc_hash, normalizer_version)
);

create index if not exists snapshots_source_fetched_idx
  on snapshots (source_id, fetched_at desc);

create table if not exists extractions (
  id              uuid primary key default gen_random_uuid(),
  snapshot_id     uuid not null references snapshots(id) on delete cascade,
  model           text not null,
  practices       jsonb not null,
  created_at      timestamptz not null default now()
);

create table if not exists change_events (
  id              uuid primary key default gen_random_uuid(),
  company_id      uuid not null references companies(id) on delete cascade,
  source_id       uuid not null references policy_sources(id) on delete cascade,
  from_snapshot   uuid references snapshots(id),
  to_snapshot     uuid not null references snapshots(id),
  materiality     text not null,
  headline        text not null,
  summary         text not null,
  data_types_added    text[] not null default '{}',
  data_types_removed  text[] not null default '{}',
  quotes          jsonb not null default '[]'::jsonb,
  published_at    timestamptz not null default now()
);

create index if not exists change_events_published_idx
  on change_events (published_at desc);

create table if not exists source_attempts (
  id                  uuid primary key default gen_random_uuid(),
  source_id           uuid not null references policy_sources(id) on delete cascade,
  started_at          timestamptz not null,
  finished_at         timestamptz,
  strategy            text not null default 'http',
  status              text not null,
  http_status         integer,
  content_type        text,
  request_url         text not null,
  resolved_url        text,
  error_code          text,
  retry_count         integer not null default 0,
  byte_count          integer,
  normalizer_version  text,
  snapshot_id         uuid references snapshots(id) on delete set null,
  observation_id      uuid,
  check (status in ('succeeded', 'failed', 'blocked')),
  check (
    error_code is null
    or error_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx', 'http_429',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network',
      'blocked', 'robots', 'ssrf', 'oversize', 'moved'
    )
  )
);

create index if not exists source_attempts_source_started_idx
  on source_attempts (source_id, started_at desc);

create table if not exists observations (
  id                    uuid primary key default gen_random_uuid(),
  source_id             uuid not null references policy_sources(id) on delete cascade,
  snapshot_id           uuid not null references snapshots(id) on delete restrict,
  attempt_id            uuid not null references source_attempts(id) on delete restrict,
  observed_at           timestamptz not null,
  region                text not null,
  previous_snapshot_id  uuid references snapshots(id) on delete restrict
);

create index if not exists observations_source_observed_idx
  on observations (source_id, observed_at desc);

create index if not exists observations_snapshot_idx
  on observations (snapshot_id);

create table if not exists document_changes (
  id                      uuid primary key default gen_random_uuid(),
  company_id              uuid not null references companies(id) on delete cascade,
  source_id               uuid not null references policy_sources(id) on delete cascade,
  from_snapshot_id        uuid references snapshots(id) on delete restrict,
  to_snapshot_id          uuid not null references snapshots(id) on delete restrict,
  from_observation_id     uuid references observations(id) on delete restrict,
  to_observation_id       uuid not null references observations(id) on delete restrict,
  added_sections          text[] not null default '{}',
  removed_sections        text[] not null default '{}',
  modified_sections       text[] not null default '{}',
  normalizer_version      text not null,
  created_at              timestamptz not null default now()
);

create index if not exists document_changes_source_created_idx
  on document_changes (source_id, created_at desc);

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
