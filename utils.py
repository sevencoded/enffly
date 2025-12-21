import os
from flask import request, jsonify
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
WORKER_SECRET = os.environ["WORKER_SECRET"]

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

def require_worker_secret(fn):
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Worker-Secret") != WORKER_SECRET:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def safe_unlink(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
