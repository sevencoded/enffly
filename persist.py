# persist.py
import json
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_job(job_id, user_id, audio_path, frame_paths):
    sb.table("jobs").insert({
        "job_id": job_id,
        "user_id": user_id,
        "audio_path": audio_path,
        "frame_paths": frame_paths,
        "status": "QUEUED",
        "attempt_count": 0,
        "created_at": datetime.utcnow().isoformat()
    }).execute()


def fetch_next_job():
    res = sb.rpc("fetch_next_job").execute()
    return res.data[0] if res.data else None


def mark_processing(job_id):
    sb.table("jobs").update({
        "status": "PROCESSING",
        "attempt_count": sb.table("jobs").select("attempt_count").eq("job_id", job_id),
        "started_at": datetime.utcnow().isoformat()
    }).eq("job_id", job_id).execute()


def mark_done(job_id, **results):
    sb.table("jobs").update({
        "status": "DONE",
        "finished_at": datetime.utcnow().isoformat(),
        "results": results
    }).eq("job_id", job_id).execute()


def mark_failed(job_id, reason):
    sb.table("jobs").update({
        "status": "FAILED",
        "error_reason": reason,
        "finished_at": datetime.utcnow().isoformat()
    }).eq("job_id", job_id).execute()
