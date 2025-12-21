import os
from flask import request, jsonify
from supabase import create_client

# Supabase je OK za API i worker
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

def require_worker_secret(fn):
    def wrapper(*args, **kwargs):
        worker_secret = os.environ.get("WORKER_SECRET")  # ✅ lazy load
        if not worker_secret:
            return jsonify({"error": "server_misconfigured"}), 500

        if request.headers.get("X-Worker-Secret") != worker_secret:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def safe_unlink(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
