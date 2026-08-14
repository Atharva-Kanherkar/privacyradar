-- Current-head schema reference. Apply with `privacyradar migrate`.
-- Docker-compose may bootstrap from this file; migrate still records 0001–0010
-- and installs append-only triggers. This file matches the end state of
-- numbered migrations (tables and functions; some triggers are migration-only).

create extension if not exists pgcrypto;

create table if not exists companies (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  name          text not null,
  website       text not null,
  category      text not null default 'consumer',
  cohort        text not null default 'seed',
  owner         text not null default 'unassigned',
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
  published_at    timestamptz,
  publication_state text not null default 'detected',
  created_at      timestamptz not null default now(),
  check (
    publication_state in (
      'detected', 'analyzing', 'review_pending', 'published',
      'rejected', 'failed', 'corrected'
    )
  )
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

create table if not exists publication_revisions (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references companies(id) on delete restrict,
  observation_id      uuid not null references observations(id) on delete restrict,
  extraction_run_id   uuid not null references extraction_runs(id) on delete restrict,
  change_event_id     uuid references change_events(id) on delete restrict,
  rolls_back_id       uuid references publication_revisions(id) on delete restrict,
  revision_n          integer not null,
  state               text not null,
  actor               text not null,
  taxonomy_version    text not null default '1.0.0',
  created_at          timestamptz not null default now(),
  unique (company_id, revision_n),
  check (state in ('published', 'rolled_back')),
  check (actor ~ '^[a-z0-9][a-z0-9:_-]{1,62}$'),
  check (revision_n > 0)
);

create index if not exists publication_revisions_company_n_idx
  on publication_revisions (company_id, revision_n desc);

create table if not exists published_claims (
  id                  uuid primary key default gen_random_uuid(),
  revision_id         uuid not null references publication_revisions(id) on delete restrict,
  candidate_claim_id  uuid not null references candidate_claims(id) on delete restrict,
  claim_key           text not null,
  category            text not null,
  attribute           text not null,
  polarity            text not null,
  quote               text not null,
  snapshot_id         uuid not null references snapshots(id) on delete restrict,
  start_offset        integer not null,
  end_offset          integer not null,
  unique (revision_id, claim_key),
  check (polarity in ('disclosed', 'negated', 'unspecified')),
  check (char_length(quote) > 0),
  check (start_offset >= 0),
  check (end_offset > start_offset)
);

create index if not exists published_claims_revision_idx
  on published_claims (revision_id);

create table if not exists review_actions (
  id           uuid primary key default gen_random_uuid(),
  actor        text not null,
  action       text not null,
  target_type  text not null,
  target_id    uuid not null,
  reason       text,
  created_at   timestamptz not null default now(),
  check (actor ~ '^[a-z0-9][a-z0-9:_-]{1,62}$'),
  check (
    action in (
      'approve', 'reject', 'publish', 'rollback',
      'correct', 'acknowledge', 'decline'
    )
  ),
  check (
    reason is null
    or (
      char_length(reason) <= 64
      and reason !~ '@'
      and reason !~ '://'
    )
  )
);

create index if not exists review_actions_target_idx
  on review_actions (target_type, target_id, created_at desc);

create table if not exists corrections (
  id                       uuid primary key default gen_random_uuid(),
  company_id               uuid not null references companies(id) on delete restrict,
  target_revision_id       uuid not null references publication_revisions(id) on delete restrict,
  replacement_revision_id  uuid references publication_revisions(id) on delete restrict,
  reporter_kind            text not null,
  state                    text not null,
  public_note              text,
  actor                    text,
  created_at               timestamptz not null default now(),
  resolved_at              timestamptz,
  check (reporter_kind in ('public', 'operator')),
  check (state in ('submitted', 'acknowledged', 'reviewing', 'corrected', 'declined'))
);

create index if not exists corrections_company_created_idx
  on corrections (company_id, created_at desc);

create table if not exists product_switches (
  key         text primary key,
  enabled     boolean not null,
  updated_at  timestamptz not null default now()
);

insert into product_switches (key, enabled)
values ('publication', true)
on conflict (key) do nothing;

insert into product_switches (key, enabled)
values ('notifications', true)
on conflict (key) do nothing;

create or replace function privacyradar_reject_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception '% is append-only', tg_table_name
    using errcode = 'restrict_violation';
end;
$$;

create or replace function privacyradar_reject_bad_published_claim()
returns trigger
language plpgsql
as $$
declare
  body text;
  claim_state text;
  run_snap uuid;
begin
  select validation_state into claim_state
  from candidate_claims
  where id = new.candidate_claim_id;
  if claim_state is distinct from 'valid' then
    raise exception 'published claim must be valid'
      using errcode = 'check_violation';
  end if;
  select markdown into body from snapshots where id = new.snapshot_id;
  if body is null or position(new.quote in body) = 0 then
    raise exception 'published claim quote missing'
      using errcode = 'check_violation';
  end if;
  if substring(body from new.start_offset + 1 for (new.end_offset - new.start_offset))
     is distinct from new.quote then
    raise exception 'published claim offset mismatch'
      using errcode = 'check_violation';
  end if;
  select r.snapshot_id into run_snap
  from publication_revisions pr
  join extraction_runs r on r.id = pr.extraction_run_id
  where pr.id = new.revision_id;
  if run_snap is distinct from new.snapshot_id then
    raise exception 'published claim snapshot mismatch'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

drop trigger if exists published_claims_quote_guard on published_claims;
create trigger published_claims_quote_guard
  before insert on published_claims
  for each row execute procedure privacyradar_reject_bad_published_claim();

create or replace function privacyradar_corrections_guard()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'DELETE' then
    raise exception 'corrections is not deletable'
      using errcode = 'restrict_violation';
  end if;
  if old.id is distinct from new.id
     or old.company_id is distinct from new.company_id
     or old.target_revision_id is distinct from new.target_revision_id
     or old.reporter_kind is distinct from new.reporter_kind
     or old.created_at is distinct from new.created_at then
    raise exception 'corrections identity is immutable'
      using errcode = 'restrict_violation';
  end if;
  return new;
end;
$$;

drop trigger if exists corrections_guard on corrections;
create trigger corrections_guard
  before update or delete on corrections
  for each row execute procedure privacyradar_corrections_guard();

drop trigger if exists publication_revisions_append_only on publication_revisions;
create trigger publication_revisions_append_only
  before update or delete on publication_revisions
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists published_claims_append_only on published_claims;
create trigger published_claims_append_only
  before update or delete on published_claims
  for each row execute procedure privacyradar_reject_mutation();

drop trigger if exists review_actions_append_only on review_actions;
create trigger review_actions_append_only
  before update or delete on review_actions
  for each row execute procedure privacyradar_reject_mutation();

-- Consumer auth: Better Auth tables, region profile, consent audit, fixture inbox.

create table if not exists auth_users (
  id              text primary key,
  name            text not null default '',
  email           text not null unique,
  email_verified  boolean not null default true,
  image           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table if not exists auth_sessions (
  id           text primary key,
  expires_at   timestamptz not null,
  token        text not null unique,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  ip_address   text,
  user_agent   text,
  user_id      text not null references auth_users(id) on delete cascade
);

create index if not exists auth_sessions_user_idx on auth_sessions (user_id);

create table if not exists auth_accounts (
  id                       text primary key,
  account_id               text not null,
  provider_id              text not null,
  user_id                  text not null references auth_users(id) on delete cascade,
  access_token             text,
  refresh_token            text,
  id_token                 text,
  access_token_expires_at  timestamptz,
  refresh_token_expires_at timestamptz,
  scope                    text,
  password                 text,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

create index if not exists auth_accounts_user_idx on auth_accounts (user_id);

create table if not exists auth_verifications (
  id          text primary key,
  identifier  text not null,
  value       text not null,
  expires_at  timestamptz not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists auth_verifications_identifier_idx
  on auth_verifications (identifier);

create table if not exists consumer_profiles (
  user_id     text primary key references auth_users(id) on delete cascade,
  region      text not null default 'unspecified',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (region in ('US', 'EU', 'UK', 'other', 'unspecified'))
);

create table if not exists consent_events (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  action      text not null,
  created_at  timestamptz not null default now(),
  check (
    action in ('signup', 'region_change', 'export', 'delete_requested', 'deleted')
  )
);

create index if not exists consent_events_user_idx
  on consent_events (user_id, created_at desc);

create table if not exists auth_magic_inbox (
  id          uuid primary key default gen_random_uuid(),
  email_hash  text not null,
  url         text not null,
  created_at  timestamptz not null default now()
);

create index if not exists auth_magic_inbox_hash_idx
  on auth_magic_inbox (email_hash, created_at desc);

drop trigger if exists consent_events_append_only on consent_events;
create trigger consent_events_append_only
  before update or delete on consent_events
  for each row execute procedure privacyradar_reject_mutation();

create or replace function privacyradar_delete_consumer(p_user_id text)
returns void
language plpgsql
as $$
declare
  v_email text;
  v_hash text;
begin
  insert into consent_events (user_id, action)
  values (p_user_id, 'delete_requested');

  delete from notification_deliveries
    where outbox_id in (select id from notification_outbox where user_id = p_user_id);
  delete from notification_outbox where user_id = p_user_id;
  delete from notification_preferences where user_id = p_user_id;
  delete from product_events where user_id = p_user_id;
  delete from watches where user_id = p_user_id;

  select email into v_email from auth_users where id = p_user_id;
  if v_email is not null then
    v_hash := encode(digest(lower(btrim(v_email)), 'sha256'), 'hex');
    delete from notification_fixture_inbox where email_hash = v_hash;
    delete from auth_magic_inbox where email_hash = v_hash;
    delete from auth_sessions where user_id = p_user_id;
    delete from auth_accounts where user_id = p_user_id;
    delete from consumer_profiles where user_id = p_user_id;
    delete from auth_verifications
      where identifier in (v_email, v_hash)
         or value like '%"email":"' || replace(v_email, '"', '') || '"%';
    delete from auth_users where id = p_user_id;
  end if;

  insert into consent_events (user_id, action)
  values (p_user_id, 'deleted');
end;
$$;

create table if not exists watches (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  company_id  uuid not null references companies(id),
  status      text not null,
  source      text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (user_id, company_id),
  check (status in ('active', 'unwatched')),
  check (source in ('company_page', 'radar_onboarding', 'resume'))
);

create index if not exists watches_user_status_idx on watches (user_id, status);
create index if not exists watches_company_status_idx on watches (company_id, status);

create table if not exists product_events (
  id          uuid primary key default gen_random_uuid(),
  user_id     text,
  name        text not null,
  company_id  uuid,
  event_id    uuid,
  created_at  timestamptz not null default now(),
  check (name in ('follow', 'unfollow', 'radar_view', 'evidence_open', 'compare_start', 'compare_complete', 'compare_evidence'))
);

create index if not exists product_events_user_idx
  on product_events (user_id, created_at desc);

create table if not exists notification_preferences (
  user_id            text primary key,
  channel            text not null default 'email',
  frequency          text not null,
  muted_company_ids  uuid[] not null default '{}',
  updated_at         timestamptz not null default now(),
  check (channel = 'email'),
  check (frequency in ('immediate', 'digest_weekly', 'unsubscribed'))
);

create table if not exists notification_fanout_jobs (
  id               uuid primary key default gen_random_uuid(),
  event_id         uuid not null references change_events(id),
  kind             text not null,
  state            text not null,
  cursor_user_id   text,
  expected_count   integer,
  written_count    integer not null default 0,
  claimed_at       timestamptz,
  claimed_by       text,
  lease_expires_at timestamptz,
  created_at       timestamptz not null default now(),
  unique (event_id, kind),
  check (kind in ('publish', 'correction')),
  check (state in ('pending', 'running', 'done', 'failed'))
);

create index if not exists notification_fanout_claim_idx
  on notification_fanout_jobs (created_at)
  where state in ('pending', 'running');

create table if not exists notification_outbox (
  id               uuid primary key default gen_random_uuid(),
  user_id          text not null,
  event_id         uuid not null references change_events(id),
  channel          text not null,
  revision         integer not null,
  kind             text not null,
  state            text not null,
  attempt_count    integer not null default 0,
  next_attempt_at  timestamptz not null default now(),
  claimed_at       timestamptz,
  claimed_by       text,
  lease_expires_at timestamptz,
  created_at       timestamptz not null default now(),
  unique (user_id, event_id, channel, revision),
  check (channel = 'email'),
  check (kind in ('publish', 'correction')),
  check (state in ('pending', 'claimed', 'sent', 'suppressed', 'failed', 'cancelled')),
  check (revision >= 1)
);

create index if not exists notification_outbox_claim_idx
  on notification_outbox (next_attempt_at)
  where state in ('pending', 'failed', 'claimed');

create table if not exists notification_deliveries (
  id                   uuid primary key default gen_random_uuid(),
  outbox_id            uuid not null references notification_outbox(id) on delete cascade,
  provider             text not null,
  provider_message_id  text,
  provider_event_id    text,
  state                text not null,
  created_at           timestamptz not null default now(),
  check (
    state in ('sent', 'delivered', 'bounced', 'complained', 'failed', 'suppressed')
  )
);

create unique index if not exists notification_deliveries_one_sent
  on notification_deliveries (outbox_id)
  where state = 'sent';

create unique index if not exists notification_deliveries_provider_event
  on notification_deliveries (provider_event_id)
  where provider_event_id is not null;

create table if not exists notification_suppressions (
  email_hash  text primary key,
  reason      text not null,
  created_at  timestamptz not null default now(),
  check (reason in ('bounce', 'complaint', 'unsubscribe'))
);

create table if not exists notification_fixture_inbox (
  id          uuid primary key default gen_random_uuid(),
  email_hash  text not null,
  subject     text not null,
  body_text   text not null,
  body_html   text not null,
  created_at  timestamptz not null default now()
);

create index if not exists notification_fixture_inbox_hash_idx
  on notification_fixture_inbox (email_hash, created_at desc);

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

