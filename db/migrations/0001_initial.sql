-- privacyradar source of truth.
-- Hash-first: LLM rows are only written when a snapshot hash changes.

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
  id            uuid primary key default gen_random_uuid(),
  company_id    uuid not null references companies(id) on delete cascade,
  kind          text not null default 'privacy', -- privacy | tos | dpa
  url           text not null,
  region        text not null default 'global',
  enabled       boolean not null default true,
  crawl_delay_s integer not null default 2,
  unique (company_id, kind, region)
);

create table if not exists snapshots (
  id              uuid primary key default gen_random_uuid(),
  source_id       uuid not null references policy_sources(id) on delete cascade,
  fetched_at      timestamptz not null default now(),
  http_status     integer,
  content_type    text,
  raw_html        text,
  markdown        text,
  doc_hash        text not null,
  section_hashes  jsonb not null default '{}'::jsonb,
  fetch_error     text,
  unique (source_id, doc_hash)
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
  materiality     text not null, -- cosmetic | material | unknown
  headline        text not null,
  summary         text not null,
  data_types_added    text[] not null default '{}',
  data_types_removed  text[] not null default '{}',
  quotes          jsonb not null default '[]'::jsonb,
  published_at    timestamptz not null default now()
);

create index if not exists change_events_published_idx
  on change_events (published_at desc);
