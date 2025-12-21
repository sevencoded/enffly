import os
import time
import traceback
from supabase import create_client

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from hash_chain import chain_hash
from persist import persist_result

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

POLL_INTERVAL = 2

def fetch_job():
    res = supabase.rpc("fetch_next_job").execute()
    return res.data[0] if res.data else None

def run():
    while True:
        job = fetch_job()
        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        job_id = job["id"]
        try:
            audio_path = job["audio_path"]
            frames = job["frame_paths"]

            enf = extract_enf_from_wav(audio_path)
            enf_hash = enf["hash"]
            enf_png = enf["png_path"]

            audio_fp = extract_audio_fingerprint(audio_path)

            phashes = []
            for p in frames:
                with open(p, "rb") as f:
                    phashes.append(phash_from_image_bytes(f.read()))

            persist_result(
                job=job,
                enf=enf,
                audio_fp=audio_fp,
                phashes=phashes
            )

            supabase.table("forensic_jobs").update({
                "status": "DONE",
                "finished_at": "now()"
            }).eq("id", job_id).execute()

        except Exception as e:
            supabase.table("forensic_jobs").update({
                "status": "FAILED",
                "error_reason": str(e)
            }).eq("id", job_id).execute()

        finally:
            os.system(f"rm -rf /data/jobs/{job_id}")

if __name__ == "__main__":
    run()
