-- Transactional change alerts: one fan-out job per published event, then outbox.

insert into product_switches (key, enabled)
values ('notifications', true)
on conflict (key) do nothing;

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
  outbox_id            uuid references notification_outbox(id) on delete cascade,
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
