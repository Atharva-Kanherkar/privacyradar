-- Watches and privacy-minimal product events for My Radar.

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
  check (name in ('follow', 'unfollow', 'radar_view', 'evidence_open'))
);

create index if not exists product_events_user_idx
  on product_events (user_id, created_at desc);

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

  delete from product_events where user_id = p_user_id;
  delete from watches where user_id = p_user_id;

  select email into v_email from auth_users where id = p_user_id;
  if v_email is not null then
    v_hash := encode(digest(lower(btrim(v_email)), 'sha256'), 'hex');
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
