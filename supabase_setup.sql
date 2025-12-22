-- Enffly / ENF queue schema + concurrency-safe job fetch
-- Run in Supabase SQL editor.

-- (Optional) enable pgcrypto if you want gen_random_uuid() defaults.
-- create extension if not exists pgcrypto;

create table if not exists public.forensic_chain_head (
  user_id text primary key,
  head_hash text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.forensic_jobs (
  id uuid primary key,
  user_id text not null,
  audio_path text not null,
  frame_paths text[],
  name text,
  status text not null default 'QUEUED'
    check (status in ('QUEUED','PROCESSING','DONE','FAILED')),
  attempt_count integer not null default 0,
  error_reason text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create table if not exists public.forensic_results (
  id uuid primary key,
  user_id text not null,
  created_at timestamptz not null default now(),
  clip_seconds numeric,
  clip_sha256 text not null,
  enf_hash text not null,
  enf_quality numeric,
  enf_freq_mean numeric,
  enf_freq_std numeric,
  audio_fp text,
  audio_fp_algo text,
  video_phash text,
  chain_prev text,
  chain_hash text not null,
  enf_png_path text,
  enf_trace_path text,
  enf_spectrogram_path text,
  name text not null
);

-- Performance indexes
create index if not exists idx_forensic_jobs_status_created
  on public.forensic_jobs (status, created_at);

create index if not exists idx_forensic_jobs_user_created
  on public.forensic_jobs (user_id, created_at desc);

create index if not exists idx_forensic_results_user_created
  on public.forensic_results (user_id, created_at desc);

-- Concurrency-safe: claim one QUEUED job and mark PROCESSING
create or replace function public.fetch_next_job()
returns setof public.forensic_jobs
language sql
as $$
  update public.forensic_jobs j
     set status = 'PROCESSING',
         started_at = now(),
         error_reason = null
   where j.id = (
     select id
       from public.forensic_jobs
      where status = 'QUEUED'
      order by created_at
      limit 1
      for update skip locked
   )
  returning *;
$$;
