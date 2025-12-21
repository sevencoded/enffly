import os
import uuid
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

DATA_DIR = "/data/jobs"
os.makedirs(DATA_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload():
    user_id = request.form.get("user_id")
    audio = request.files.get("audio")
    frames = [
        request.files.get("frame1"),
        request.files.get("frame2"),
        request.files.get("frame3"),
    ]

    if not user_id or not audio or any(f is None for f in frames):
        return jsonify({"error": "missing inputs"}), 400

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(DATA_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    audio_path = os.path.join(job_dir, "audio.wav")
    audio.save(audio_path)

    frame_paths = []
    for i, f in enumerate(frames):
        p = os.path.join(job_dir, f"frame{i+1}.png")
        f.save(p)
        frame_paths.append(p)

    supabase.table("forensic_jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "audio_path": audio_path,
        "frame_paths": frame_paths,
        "status": "QUEUED"
    }).execute()

    return jsonify({
        "job_id": job_id,
        "status": "QUEUED"
    })
