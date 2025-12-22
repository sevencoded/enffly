import os
import uuid
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(os.environ.get("ENFFLY_DATA_DIR", "/data/jobs"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/upload")
def upload():
    # NOTE: For production, do NOT trust user_id from the form.
    # Ideally verify Supabase JWT and derive user_id from it.
    user_id = request.form.get("user_id")
    proof_name = (request.form.get("proof_name") or request.form.get("name") or "").strip()
    audio = request.files.get("audio")

    # Accept both naming schemes:
    # - frame1/frame2/frame3 (old)
    # - frame_1/frame_2/frame_3 (Flutter current)
    frames = [
        request.files.get("frame1") or request.files.get("frame_1"),
        request.files.get("frame2") or request.files.get("frame_2"),
        request.files.get("frame3") or request.files.get("frame_3"),
    ]

    if not user_id or not audio or any(f is None for f in frames):
        return jsonify({"error": "missing inputs (user_id, audio, frame1-3 or frame_1-3)"}), 400

    job_id = str(uuid.uuid4())
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save audio with real extension (worker converts to wav if needed)
    audio_name = (audio.filename or "audio").lower()
    audio_ext = Path(audio_name).suffix if Path(audio_name).suffix else ".wav"
    if audio_ext not in ALLOWED_AUDIO_EXT:
        return jsonify({"error": f"unsupported audio type: {audio_ext}"}), 400

    audio_path = job_dir / f"audio{audio_ext}"
    audio.save(str(audio_path))

    frame_paths = []
    for i, f in enumerate(frames, start=1):
        img_name = (f.filename or f"frame{i}.png").lower()
        img_ext = Path(img_name).suffix if Path(img_name).suffix else ".png"
        if img_ext not in ALLOWED_IMAGE_EXT:
            return jsonify({"error": f"unsupported image type: {img_ext}"}), 400

        p = job_dir / f"frame{i}{img_ext}"
        f.save(str(p))
        frame_paths.append(str(p))

    supabase.table("forensic_jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "audio_path": str(audio_path),
        "frame_paths": frame_paths,
        "status": "QUEUED",
        "name": proof_name or "ENF Proof",
    }).execute()

    return jsonify({"job_id": job_id, "status": "QUEUED"}), 202

