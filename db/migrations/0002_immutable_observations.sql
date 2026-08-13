-- Immutable snapshots, append-only observations, source attempts, and health.
-- Additive. Does not rewrite 0001 checksums. Idempotent on re-apply of the file
-- only before this version is recorded; after recording, the runner skips it.

alter table policy_sources
  add column if not exists current_snapshot_id uuid,
  add column if not exists current_observation_id uuid,
  add column if not exists health_status text not null default 'pending',
  add column if not exists last_attempt_at timestamptz,
  add column if not exists last_success_at timestamptz,
  add column if not exists last_failure_code text,
  add column if not exists consecutive_failures integer not null default 0;

alter table policy_sources drop constraint if exists policy_sources_health_status_check;
alter table policy_sources
  add constraint policy_sources_health_status_check
  check (health_status in ('pending', 'healthy', 'degraded', 'quarantined'));

alter table policy_sources drop constraint if exists policy_sources_last_failure_code_check;
alter table policy_sources
  add constraint policy_sources_last_failure_code_check
  check (
    last_failure_code is null
    or last_failure_code in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network', 'blocked'
    )
  );

alter table snapshots
  add column if not exists final_url text,
  add column if not exists language text,
  add column if not exists region text not null default 'global',
  add column if not exists strategy text not null default 'http',
  add column if not exists byte_count integer,
  add column if not exists raw_sha256 text,
  add column if not exists normalized_sha256 text,
  add column if not exists normalizer_version text not null default '1.0.0',
  add column if not exists is_valid boolean not null default true;

alter table snapshots drop constraint if exists snapshots_source_id_doc_hash_key;
alter table snapshots drop constraint if exists snapshots_source_hash_normalizer_key;
alter table snapshots
  add constraint snapshots_source_hash_normalizer_key
  unique (source_id, doc_hash, normalizer_version);

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

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'policy_sources_current_snapshot_fk'
  ) then
    alter table policy_sources
      add constraint policy_sources_current_snapshot_fk
      foreign key (current_snapshot_id) references snapshots(id) on delete set null;
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'policy_sources_current_observation_fk'
  ) then
    alter table policy_sources
      add constraint policy_sources_current_observation_fk
      foreign key (current_observation_id) references observations(id) on delete set null;
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'source_attempts_observation_fk'
  ) then
    alter table source_attempts
      add constraint source_attempts_observation_fk
      foreign key (observation_id) references observations(id) on delete set null;
  end if;
end
$$;

-- Backfill snapshot metadata from existing 0001 rows.
update snapshots
set
  raw_sha256 = encode(sha256(convert_to(coalesce(raw_html, ''), 'UTF8')), 'hex'),
  normalized_sha256 = doc_hash,
  byte_count = octet_length(convert_to(coalesce(raw_html, markdown, ''), 'UTF8')),
  final_url = coalesce(final_url, (
    select ps.url from policy_sources ps where ps.id = snapshots.source_id
  )),
  region = coalesce(nullif(region, ''), (
    select ps.region from policy_sources ps where ps.id = snapshots.source_id
  ), 'global')
where raw_sha256 is null or normalized_sha256 is null;

update snapshots
set is_valid = false
where fetch_error is not null
   or markdown is null
   or btrim(markdown) = ''
   or doc_hash = 'empty'
   or char_length(btrim(markdown)) < 40;

update snapshots
set is_valid = true
where fetch_error is null
  and markdown is not null
  and char_length(btrim(markdown)) >= 40
  and doc_hash <> 'empty';

insert into source_attempts (
  source_id, started_at, finished_at, strategy, status,
  http_status, content_type, request_url, resolved_url,
  snapshot_id, byte_count, normalizer_version
)
select
  s.source_id,
  s.fetched_at,
  s.fetched_at,
  s.strategy,
  'succeeded',
  s.http_status,
  s.content_type,
  ps.url,
  coalesce(s.final_url, ps.url),
  s.id,
  s.byte_count,
  s.normalizer_version
from snapshots s
join policy_sources ps on ps.id = s.source_id
where s.is_valid
  and not exists (
    select 1 from source_attempts a where a.snapshot_id = s.id
  );

insert into source_attempts (
  source_id, started_at, finished_at, strategy, status,
  http_status, content_type, request_url, resolved_url,
  error_code, byte_count, normalizer_version
)
select
  s.source_id,
  s.fetched_at,
  s.fetched_at,
  s.strategy,
  'failed',
  s.http_status,
  s.content_type,
  ps.url,
  coalesce(s.final_url, ps.url),
  case
    when s.fetch_error in (
      'timeout', 'dns', 'tls', 'http_4xx', 'http_5xx',
      'empty', 'short', 'wrong_type', 'normalize_failed', 'network', 'blocked'
    ) then s.fetch_error
    when s.doc_hash = 'empty' or coalesce(s.markdown, '') = '' then 'empty'
    else 'network'
  end,
  s.byte_count,
  s.normalizer_version
from snapshots s
join policy_sources ps on ps.id = s.source_id
where not s.is_valid
  and not exists (
    select 1 from source_attempts a
    where a.source_id = s.source_id
      and a.started_at = s.fetched_at
      and a.status = 'failed'
  );

insert into observations (
  source_id, snapshot_id, attempt_id, observed_at, region, previous_snapshot_id
)
select distinct on (s.id)
  s.source_id,
  s.id,
  a.id,
  s.fetched_at,
  s.region,
  null
from snapshots s
join source_attempts a
  on a.snapshot_id = s.id and a.status = 'succeeded'
where s.is_valid
  and not exists (
    select 1 from observations o where o.snapshot_id = s.id
  )
order by s.id, a.started_at;

update source_attempts a
set observation_id = o.id
from observations o
where o.attempt_id = a.id
  and a.observation_id is null;

update policy_sources ps
set
  current_snapshot_id = x.snapshot_id,
  current_observation_id = x.observation_id,
  health_status = 'healthy',
  last_success_at = x.observed_at,
  last_attempt_at = coalesce(ps.last_attempt_at, x.observed_at)
from (
  select distinct on (o.source_id)
    o.source_id,
    o.snapshot_id,
    o.id as observation_id,
    o.observed_at
  from observations o
  order by o.source_id, o.observed_at desc
) x
where ps.id = x.source_id
  and ps.current_snapshot_id is null;

create or replace function privacyradar_reject_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception '% is append-only', tg_table_name
    using errcode = 'restrict_violation';
end;
$$;

drop trigger if exists snapshots_append_only on snapshots;
create trigger snapshots_append_only
  before update or delete on snapshots
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists observations_append_only on observations;
create trigger observations_append_only
  before update or delete on observations
  for each row execute procedure privacyradar_reject_mutation();
