import os
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from supabase import create_client

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from persist import persist_result

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ENF_BUCKET = os.environ.get("ENFFLY_RESULTS_BUCKET", "main_videos")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL = float(os.environ.get("ENFFLY_POLL_INTERVAL", "2"))
MAX_ATTEMPTS = int(os.environ.get("ENFFLY_MAX_ATTEMPTS", "3"))

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def fetch_job():
    # Requires RPC function fetch_next_job() in Supabase SQL.
    res = supabase.rpc("fetch_next_job").execute()
    return res.data[0] if res.data else None

def ensure_wav(audio_path: str) -> str:
    """Convert to wav if needed (fpcalc + scipy wav reader require WAV)."""
    p = Path(audio_path)
    if p.suffix.lower() == ".wav":
        return str(p)

    out = p.with_suffix(".wav")
    cmd = ["ffmpeg", "-y", "-i", str(p), "-ac", "1", "-ar", "44100", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg convert failed: {r.stderr.strip()[:200]}")
    return str(out)

def upload_bytes(bucket: str, path: str, data: bytes, content_type: str):
    # supabase-py v2 uses file_options
    file_options = {"content-type": content_type, "upsert": "true"}
    supabase.storage.from_(bucket).upload(path, data, file_options=file_options)

def run():
    while True:
        job = fetch_job()
        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        job_id = job["id"]
        user_id = job["user_id"]

        try:
            audio_path = ensure_wav(job["audio_path"])
            frame_paths = job.get("frame_paths") or []

            # --- ENF ---
            (enf_hash, trace_png_bytes, spec_png_bytes, quality, f_mean, f_std) = extract_enf_from_wav(audio_path)

            # Upload result images to Supabase Storage (ONLY results; no raw audio/frames)
            base_path = f"enf_results/{user_id}/{job_id}"
            trace_path = f"{base_path}/enf_trace.png"
            spec_path = f"{base_path}/enf_spectrogram.png"

            upload_bytes(ENF_BUCKET, trace_path, trace_png_bytes, "image/png")
            upload_bytes(ENF_BUCKET, spec_path, spec_png_bytes, "image/png")

            # --- audio fingerprint ---
            fp = extract_audio_fingerprint(audio_path)
            audio_fp = {"fp": fp, "algo": "chromaprint_fpcalc_raw"}

            # --- pHash from 3 frames ---
            phashes = []
            for p in frame_paths:
                with open(p, "rb") as f:
                    phashes.append(phash_from_image_bytes(f.read()))
            combined_phash = "|".join(phashes)

            # --- persist result rows + chain ---
            enf = {
                "enf_hash": enf_hash,
                "quality": quality,
                "f_mean": f_mean,
                "f_std": f_std,
                "clip_seconds": job.get("clip_seconds"),  # optional if you later add it
                "png_path": trace_path,
                "trace_path": trace_path,  # kept for compatibility
                "spectrogram_path": spec_path,
            }
            persist_result(job=job, enf=enf, audio_fp=audio_fp, video_phash=combined_phash)

            supabase.table("forensic_jobs").update({
                "status": "DONE",
                "finished_at": utc_now_iso(),
                "error_reason": None,
            }).eq("id", job_id).execute()

        except Exception as e:
            # retry logic
            attempt = int(job.get("attempt_count") or 0) + 1
            new_status = "QUEUED" if attempt < MAX_ATTEMPTS else "FAILED"

            supabase.table("forensic_jobs").update({
                "status": new_status,
                "attempt_count": attempt,
                "error_reason": str(e)[:500],
                "finished_at": utc_now_iso() if new_status == "FAILED" else None,
            }).eq("id", job_id).execute()

        finally:
            # Cleanup local job folder (audio + frames)
            job_dir = Path("/data/jobs") / str(job_id)
            try:
                subprocess.run(["rm", "-rf", str(job_dir)], check=False)
            except Exception:
                pass

if __name__ == "__main__":
    run()
