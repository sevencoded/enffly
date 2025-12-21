# persist.py
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_job(job_id, user_id, audio_path, frame_paths):
    sb.table("forensic_jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "audio_path": audio_path,
        "frame_paths": frame_paths,
        "status": "QUEUED",
        "attempt_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }).execute()


def fetch_next_job():
    res = sb.rpc("fetch_next_forensic_job").execute()

    # RPC vraća ili dict ili None
    if not res.data:
        return None

    return res.data


def mark_processing(job_id):
    sb.table("forensic_jobs").update({
        "status": "PROCESSING",
        "started_at": datetime.utcnow().isoformat()
    }).eq("id", job_id).execute()


def mark_done(job_id):
    sb.table("forensic_jobs").update({
        "status": "DONE",
        "finished_at": datetime.utcnow().isoformat()
    }).eq("id", job_id).execute()


def mark_failed(job_id, reason):
    sb.table("forensic_jobs").update({
        "status": "FAILED",
        "error_reason": str(reason),
        "finished_at": datetime.utcnow().isoformat()
    }).eq("id", job_id).execute()
