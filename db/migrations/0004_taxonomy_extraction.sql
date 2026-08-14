-- Versioned taxonomy and append-only extraction candidate runs.

create table if not exists taxonomy_versions (
  version          text primary key,
  schema_checksum  text not null,
  created_at       timestamptz not null default now()
);

insert into taxonomy_versions (version, schema_checksum)
values (
  '1.0.0',
  '3ca634aef1ce3f94d860952aaae7c265cccc4c73c7d30dd544b92892b82f0908'
)
on conflict (version) do nothing;

create table if not exists extraction_runs (
  id                   uuid primary key default gen_random_uuid(),
  observation_id       uuid not null references observations(id) on delete restrict,
  snapshot_id          uuid not null references snapshots(id) on delete restrict,
  taxonomy_version     text not null references taxonomy_versions(version),
  prompt_version       text not null,
  model                text not null,
  provider_request_id  text,
  status               text not null,
  confidence           numeric,
  latency_ms           integer,
  cost_usd             numeric,
  created_at           timestamptz not null default now(),
  check (status in ('succeeded', 'failed', 'invalid'))
);

create index if not exists extraction_runs_observation_created_idx
  on extraction_runs (observation_id, created_at desc);

create table if not exists candidate_claims (
  id                 uuid primary key default gen_random_uuid(),
  run_id             uuid not null references extraction_runs(id) on delete restrict,
  claim_key          text not null,
  category           text not null,
  attribute          text not null,
  polarity           text not null,
  confidence         numeric,
  validation_state   text not null,
  payload            jsonb not null default '{}'::jsonb,
  check (
    validation_state in ('valid', 'unsupported', 'invalid_category')
  ),
  check (polarity in ('disclosed', 'negated', 'unspecified'))
);

create index if not exists candidate_claims_run_key_idx
  on candidate_claims (run_id, claim_key);

create table if not exists evidence_spans (
  id                  uuid primary key default gen_random_uuid(),
  claim_id            uuid not null references candidate_claims(id) on delete restrict,
  snapshot_id         uuid not null references snapshots(id) on delete restrict,
  quote               text not null,
  section             text,
  start_offset        integer,
  end_offset          integer,
  context             text,
  validation_result   text not null,
  check (validation_result in ('exact', 'normalized', 'missing'))
);

drop trigger if exists taxonomy_versions_append_only on taxonomy_versions;
create trigger taxonomy_versions_append_only
  before update or delete on taxonomy_versions
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists extraction_runs_append_only on extraction_runs;
create trigger extraction_runs_append_only
  before update or delete on extraction_runs
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists candidate_claims_append_only on candidate_claims;
create trigger candidate_claims_append_only
  before update or delete on candidate_claims
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists evidence_spans_append_only on evidence_spans;
create trigger evidence_spans_append_only
  before update or delete on evidence_spans
  for each row execute procedure privacyradar_reject_mutation();
