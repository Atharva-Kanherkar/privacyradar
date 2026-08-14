-- Cited assistant kill switch and usage counters. Additive.

insert into product_switches (key, enabled)
values ('assistant', false)
on conflict (key) do nothing;

create table if not exists assistant_usage (
  identity_hash  text not null,
  day            date not null default (timezone('utc', now()))::date,
  count          integer not null default 0,
  updated_at     timestamptz not null default now(),
  primary key (identity_hash, day),
  check (count >= 0),
  check (char_length(identity_hash) = 64)
);
