-- ============================================
-- Forensic results table
-- ============================================
create table if not exists public.forensic_results (
  id uuid primary key,

  -- owner
  user_id text not null,

  -- HUMAN-READABLE PROOF NAME (REQUIRED)
  name text not null,

  -- metadata
  created_at timestamptz not null default now(),
  clip_seconds numeric,
  clip_sha256 text not null,

  -- ENF
  enf_hash text not null,
  enf_quality numeric,
  enf_freq_mean numeric,
  enf_freq_std numeric,

  -- audio fingerprint
  audio_fp text,
  audio_fp_algo text,

  -- video fingerprint
  video_phash text,

  -- hash chain
  chain_prev text,
  chain_hash text not null,

  -- storage paths
  enf_trace_path text,
  enf_spectrogram_path text
);

-- --------------------------------------------
-- UNIQUE: proof name must be unique PER USER
-- --------------------------------------------
create unique index if not exists forensic_results_user_name_unique
on public.forensic_results (user_id, name);


-- ============================================
-- Per-user chain head table
-- ============================================
create table if not exists public.forensic_chain_head (
  user_id text primary key,
  head_hash text not null,
  updated_at timestamptz not null default now()
);
