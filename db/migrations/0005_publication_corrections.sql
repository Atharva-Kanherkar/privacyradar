-- Publication revisions, published claims, review audit, corrections, feature switch.

alter table change_events
  add column if not exists publication_state text;

update change_events
set publication_state = 'published'
where publication_state is null;

alter table change_events
  alter column publication_state set default 'detected';

alter table change_events
  alter column publication_state set not null;

alter table change_events
  drop constraint if exists change_events_publication_state_check;

alter table change_events
  add constraint change_events_publication_state_check
  check (
    publication_state in (
      'detected', 'analyzing', 'review_pending', 'published',
      'rejected', 'failed', 'corrected'
    )
  );

alter table change_events
  alter column published_at drop not null;

alter table change_events
  add column if not exists created_at timestamptz;

update change_events
set created_at = coalesce(published_at, now())
where created_at is null;

alter table change_events
  alter column created_at set default now();

alter table change_events
  alter column created_at set not null;

create table if not exists publication_revisions (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references companies(id) on delete restrict,
  observation_id      uuid not null references observations(id) on delete restrict,
  extraction_run_id   uuid not null references extraction_runs(id) on delete restrict,
  change_event_id     uuid references change_events(id) on delete restrict,
  revision_n          integer not null,
  state               text not null,
  actor               text not null,
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

create or replace function privacyradar_reject_bad_published_claim()
returns trigger
language plpgsql
as $$
declare
  body text;
  claim_state text;
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
