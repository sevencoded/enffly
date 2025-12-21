import os
import hashlib
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def persist_result(*, job: dict, enf: dict, audio_fp: dict, video_phash: str):
    """
    Writes a row to forensic_results and updates forensic_chain_head.
    Expects:
      - job: forensic_jobs row (dict)
      - enf: dict with fields:
          enf_hash, quality, f_mean, f_std, clip_seconds,
          trace_path, spectrogram_path (storage paths or None)
      - audio_fp: dict with fields: fp, algo
      - video_phash: string (single combined phash)
    """
    user_id = job["user_id"]
    job_id = job["id"]

    # Chain head
    head = supabase.table("forensic_chain_head").select("head_hash").eq("user_id", user_id).execute()
    prev = head.data[0]["head_hash"] if head.data else None

    # Build a deterministic chain payload (keep it stable)
    payload = "|".join([
        str(prev or ""),
        str(job_id),
        str(user_id),
        str(enf["enf_hash"]),
        str(audio_fp.get("fp") or ""),
        str(video_phash or ""),
    ]).encode("utf-8")

    chain_hash = _sha256_hex(payload)

    supabase.table("forensic_results").insert({
        "id": job_id,
        "user_id": user_id,
        "clip_seconds": enf.get("clip_seconds"),
        "clip_sha256": enf["enf_hash"],
        "enf_hash": enf["enf_hash"],
        "enf_quality": enf.get("quality"),
        "enf_freq_mean": enf.get("f_mean"),
        "enf_freq_std": enf.get("f_std"),
        "audio_fp": audio_fp.get("fp"),
        "audio_fp_algo": audio_fp.get("algo"),
        "video_phash": video_phash,
        "chain_prev": prev,
        "chain_hash": chain_hash,
        "enf_png_path": enf.get("png_path"),
        "enf_trace_path": enf.get("trace_path"),
        "enf_spectrogram_path": enf.get("spectrogram_path"),
        "name": "ENF Proof",
    }).execute()

    supabase.table("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": chain_hash,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return chain_hash
