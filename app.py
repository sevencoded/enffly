# app.py
import os
import uuid
import tempfile
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

from persist import create_job
from utils import safe_unlink

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload():
    audio = request.files.get("audio")
    frames = [
        request.files.get("frame_1"),
        request.files.get("frame_2"),
        request.files.get("frame_3"),
    ]
    user_id = request.form.get("user_id")

    if not audio or not user_id:
        return jsonify({"error": "missing_audio_or_user"}), 400

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        audio_path = os.path.join(job_dir, "audio.wav")
        audio.save(audio_path)

        frame_paths = []
        for i, f in enumerate(frames):
            if f:
                p = os.path.join(job_dir, f"frame_{i+1}.jpg")
                f.save(p)
                frame_paths.append(p)

        create_job(
            job_id=job_id,
            user_id=user_id,
            audio_path=audio_path,
            frame_paths=frame_paths,
        )

        # USER NE ČEKA NIŠTA
        return jsonify({
            "status": "QUEUED",
            "job_id": job_id
        }), 202

    except Exception as e:
        safe_unlink(job_dir)
        return jsonify({"error": "upload_failed", "details": str(e)}), 500
