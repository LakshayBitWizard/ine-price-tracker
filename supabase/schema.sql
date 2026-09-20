-- INE Product Price Tracker — Supabase (PostgreSQL) schema
-- Run this entire script in the Supabase SQL Editor.

create extension if not exists pgcrypto;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'scrape_outcome') then
    create type public.scrape_outcome as enum ('success', 'retried', 'failed');
  end if;
end
$$;

-- ---------------------------------------------------------------------------
-- TrackedProducts
-- Products the user chose to follow. Extra storefront fields live in metadata.
-- ---------------------------------------------------------------------------
create table if not exists public."TrackedProducts" (
  id uuid primary key default gen_random_uuid(),
  store_product_id text,
  name text not null,
  url text not null,
  image_url text,
  description text,
  currency text not null default 'USD',
  current_price numeric(12, 2),
  current_stock_quantity integer,
  currently_in_stock boolean,
  scrape_interval_minutes integer not null default 120
    check (scrape_interval_minutes > 0),
  is_active boolean not null default true,
  last_successful_scrape_at timestamptz,
  last_scrape_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint tracked_products_url_unique unique (url),
  constraint tracked_products_store_id_unique unique (store_product_id),
  constraint tracked_products_current_price_nonnegative
    check (current_price is null or current_price >= 0),
  constraint tracked_products_stock_qty_nonnegative
    check (current_stock_quantity is null or current_stock_quantity >= 0)
);

create index if not exists tracked_products_is_active_idx
  on public."TrackedProducts" (is_active)
  where is_active = true;

create index if not exists tracked_products_name_idx
  on public."TrackedProducts" (name);

-- ---------------------------------------------------------------------------
-- ScrapeLogs
-- One row per scrape attempt. Failures are stored; never omit them.
-- ---------------------------------------------------------------------------
create table if not exists public."ScrapeLogs" (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null
    references public."TrackedProducts" (id) on delete cascade,
  run_id uuid not null default gen_random_uuid(),
  attempted_at timestamptz not null default now(),
  outcome public.scrape_outcome not null,
  attempt_number integer not null default 1
    check (attempt_number >= 1),
  http_status integer,
  duration_ms integer
    check (duration_ms is null or duration_ms >= 0),
  error_message text,
  page_structure_changed boolean not null default false,
  headed boolean not null default false,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists scrape_logs_product_attempted_idx
  on public."ScrapeLogs" (product_id, attempted_at desc);

create index if not exists scrape_logs_run_id_idx
  on public."ScrapeLogs" (run_id);

create index if not exists scrape_logs_outcome_idx
  on public."ScrapeLogs" (outcome);

-- ---------------------------------------------------------------------------
-- PriceHistory
-- Only persist rows after a successful scrape with a real price and stock.
-- Do not insert on failed or empty extractions.
-- ---------------------------------------------------------------------------
create table if not exists public."PriceHistory" (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null
    references public."TrackedProducts" (id) on delete cascade,
  scrape_log_id uuid
    references public."ScrapeLogs" (id) on delete set null,
  price numeric(12, 2) not null
    check (price >= 0),
  currency text not null default 'USD',
  stock_quantity integer
    check (stock_quantity is null or stock_quantity >= 0),
  in_stock boolean not null,
  scraped_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists price_history_product_scraped_idx
  on public."PriceHistory" (product_id, scraped_at desc);

create index if not exists price_history_scrape_log_idx
  on public."PriceHistory" (scrape_log_id);

-- Keep TrackedProducts.updated_at current on row changes.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists tracked_products_set_updated_at on public."TrackedProducts";
create trigger tracked_products_set_updated_at
  before update on public."TrackedProducts"
  for each row
  execute procedure public.set_updated_at();

-- Backend on Render should use the service_role key (bypasses RLS).
-- No anon write access: the dashboard talks to Express/Django, not the DB.
alter table public."TrackedProducts" enable row level security;
alter table public."PriceHistory" enable row level security;
alter table public."ScrapeLogs" enable row level security;

-- Verify the three assignment tables exist.
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('TrackedProducts', 'PriceHistory', 'ScrapeLogs')
order by table_name;
