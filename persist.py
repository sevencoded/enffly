# persist.py
from datetime import datetime
import os
from supabase import create_client

# ================= CONFIG =================

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= JOB CREATION =================

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

# ================= JOB FETCH =================
# OVO JE FIX ZA KeyError: 0

def fetch_next_job():
    """
    fetch_next_forensic_job RPC može vratiti:
    - None
    - dict (single row)
    - list (setof)
    """
    res = sb.rpc("fetch_next_forensic_job").execute()

    if not res.data:
        return None

    # Ako RPC vraća jedan RECORD
    if isinstance(res.data, dict):
        return res.data

    # Ako RPC vraća SETOF
    if isinstance(res.data, list) and len(res.data) > 0:
        return res.data[0]

    return None

# ================= JOB STATE UPDATES =================

def mark_processing(job_id):
    sb.table("forensic_jobs").update({
        "status": "PROCESSING",
        "attempt_count": sb.table("forensic_jobs")
            .select("attempt_count")
            .eq("id", job_id),
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
        "error_reason": reason,
        "finished_at": datetime.utcnow().isoformat()
    }).eq("id", job_id).execute()
