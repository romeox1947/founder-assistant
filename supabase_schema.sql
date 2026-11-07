-- Run this once in Supabase Dashboard > SQL Editor.
create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    source_type text not null,
    source_url text not null unique,
    title text,
    content text,
    metadata jsonb not null default '{}'::jsonb,
    content_hash text,
    created_at timestamptz not null default now()
);

create index if not exists documents_source_type_idx on public.documents(source_type);
create index if not exists documents_created_at_idx on public.documents(created_at desc);

-- This demo uses the Supabase service-role key server-side in Streamlit secrets.
-- Never expose the service-role key in frontend JavaScript or a public repository.
alter table public.documents enable row level security;
-- No public policies are created. The service-role key bypasses RLS.
