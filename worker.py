import os
import time
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path

from supabase import create_client

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from persist import persist_result

# ---------------- CONFIG ----------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ENF_BUCKET = os.environ.get("ENFFLY_RESULTS_BUCKET", "main_videos")

POLL_INTERVAL = float(os.environ.get("ENFFLY_POLL_INTERVAL", "2"))
MAX_ATTEMPTS = int(os.environ.get("ENFFLY_MAX_ATTEMPTS", "3"))

# Force system ffmpeg (avoid imageio conflicts)
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- HELPERS ----------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def fetch_job():
    res = supabase.rpc("fetch_next_job").execute()
    return res.data[0] if res.data else None

def ensure_wav(audio_path: str) -> str:
    """
    Always return a WAV file.
    ENF + fpcalc REQUIRE WAV.
    """
    p = Path(audio_path)

    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: {p}")

    if p.suffix.lower() == ".wav":
        return str(p)

    wav_path = p.with_suffix(".wav")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(p),
        "-ac", "1",
        "-ar", "44100",
        str(wav_path),
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg convert failed: {r.stderr.strip()[:300]}"
        )

    return str(wav_path)

def upload_bytes(bucket: str, path: str, data: bytes, content_type: str):
    file_options = {"content-type": content_type, "upsert": "true"}
    supabase.storage.from_(bucket).upload(
        path,
        data,
        file_options=file_options,
    )

# ---------------- MAIN LOOP ----------------
def run():
    print("ENFFLY WORKER STARTED")

    while True:
        job = fetch_job()

        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        job_id = job["id"]
        user_id = job["user_id"]

        print(f"[worker] Picked job {job_id}")

        try:
            # -------- PATHS --------
            audio_wav = ensure_wav(job["audio_path"])
            frame_paths = job.get("frame_paths") or []

            # -------- ENF --------
            (
                enf_hash,
                trace_png_bytes,
                spec_png_bytes,
                quality,
                f_mean,
                f_std,
            ) = extract_enf_from_wav(audio_wav)

            base_path = f"enf_results/{user_id}/{job_id}"
            trace_path = f"{base_path}/enf_trace.png"
            spec_path = f"{base_path}/enf_spectrogram.png"

            upload_bytes(
                ENF_BUCKET,
                trace_path,
                trace_png_bytes,
                "image/png",
            )
            upload_bytes(
                ENF_BUCKET,
                spec_path,
                spec_png_bytes,
                "image/png",
            )

            # -------- AUDIO FINGERPRINT --------
            fp = extract_audio_fingerprint(audio_wav)
            audio_fp = {
                "fp": fp,
                "algo": "chromaprint_fpcalc_raw",
            }

            # -------- PHASH --------
            phashes = []
            for p in frame_paths:
                with open(p, "rb") as f:
                    phashes.append(phash_from_image_bytes(f.read()))

            combined_phash = "|".join(phashes)

            # -------- PERSIST RESULT --------
            enf = {
                "enf_hash": enf_hash,
                "quality": quality,
                "f_mean": f_mean,
                "f_std": f_std,
                "clip_seconds": job.get("clip_seconds"),
                "png_path": trace_path,
                "trace_path": trace_path,
                "spectrogram_path": spec_path,
            }

            persist_result(
                job=job,
                enf=enf,
                audio_fp=audio_fp,
                video_phash=combined_phash,
            )

            supabase.table("forensic_jobs").update({
                "status": "DONE",
                "finished_at": utc_now_iso(),
                "error_reason": None,
            }).eq("id", job_id).execute()

            print(f"[worker] DONE {job_id}")

        except Exception as e:
            print(f"[worker] ERROR {job_id}")
            traceback.print_exc()

            attempt = int(job.get("attempt_count") or 0) + 1
            new_status = "QUEUED" if attempt < MAX_ATTEMPTS else "FAILED"

            supabase.table("forensic_jobs").update({
                "status": new_status,
                "attempt_count": attempt,
                "error_reason": str(e)[:500],
                "finished_at": utc_now_iso() if new_status == "FAILED" else None,
            }).eq("id", job_id).execute()

        finally:
            # -------- CLEANUP --------
            job_dir = Path("/data/jobs") / str(job_id)
            try:
                subprocess.run(
                    ["rm", "-rf", str(job_dir)],
                    check=False,
                )
            except Exception:
                pass

if __name__ == "__main__":
    run()
