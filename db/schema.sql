-- Current-head schema reference. Apply with `privacyradar migrate`.
-- Docker-compose may bootstrap from this file; migrate still records 0001+0002
-- and installs append-only triggers. This file matches the end state of
-- db/migrations/0001_initial.sql plus 0002 DDL (without DML backfill/triggers).

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
  unique (company_id, kind, region),
  check (health_status in ('pending', 'healthy', 'degraded', 'quarantined')),
  check (
    last_failure_code is null
    or last_failure_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network', 'blocked'
    )
  )
);

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
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network', 'blocked'
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
