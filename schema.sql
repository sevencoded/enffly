-- Minimal schema for saving forensic results and a per-user chain head.

create table if not exists forensic_results (
  id uuid primary key,
  user_id text not null,
  created_at timestamptz not null default now(),

  clip_seconds numeric,
  clip_sha256 text,

  enf_hash text,
  enf_quality numeric,
  enf_freq_mean numeric,
  enf_freq_std numeric,

  audio_fp text,
  audio_fp_algo text,

  video_phash text,

  chain_prev text,
  chain_hash text,

  enf_png_path text
);

-- Stores the latest chain hash per user (head).
create table if not exists forensic_chain_head (
  user_id text primary key,
  head_hash text not null,
  updated_at timestamptz not null default now()
);
