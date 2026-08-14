-- Catalog cohorts, nominations, and health snapshots. Additive.

alter table companies
  add column if not exists cohort text not null default 'seed';

alter table companies
  add column if not exists owner text not null default 'unassigned';

create table if not exists catalog_cohorts (
  key         text primary key,
  enabled     boolean not null,
  target_n    integer not null,
  notes       text,
  updated_at  timestamptz not null default now()
);

insert into catalog_cohorts (key, enabled, target_n, notes)
values
  ('seed', true, 10, 'Current hand-picked catalog. Not a 500-company claim.'),
  ('c1', false, 25, 'Disabled until two health cycles meet fetch and evidence gates.')
on conflict (key) do nothing;

create table if not exists company_requests (
  id           uuid primary key default gen_random_uuid(),
  name         text,
  website      text not null,
  category     text,
  status       text not null,
  duplicate_of uuid,
  created_at   timestamptz not null default now(),
  check (status in ('requested', 'duplicate', 'accepted', 'declined'))
);

create index if not exists company_requests_host_idx
  on company_requests (website, created_at desc);

create table if not exists catalog_health_snapshots (
  id                   uuid primary key default gen_random_uuid(),
  fetch_success_pct    numeric not null,
  evidence_valid_pct   numeric not null,
  created_at           timestamptz not null default now()
);
