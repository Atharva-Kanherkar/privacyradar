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
