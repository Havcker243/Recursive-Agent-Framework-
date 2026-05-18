create table if not exists public.public_runs (
  id text primary key,
  goal text not null,
  provider text not null,
  model text,
  status text not null,
  result jsonb,
  events jsonb not null,
  created_at double precision not null,
  published_at timestamptz not null default now(),
  event_count integer not null default 0
);

alter table public.public_runs enable row level security;

create policy "public can read published runs"
on public.public_runs
for select
to anon, authenticated
using (true);
