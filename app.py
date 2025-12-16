# app.py
import os
import tempfile
import traceback
import uuid
from flask import Flask, request, jsonify

from media import extract_audio_wav, get_media_duration_seconds
from enf import extract_enf_from_wav
from audio_fingerprint import chromaprint_fp
from video_phash import video_phash_first_frame
from hash_chain import chain_hash
from utils import sha256_file, safe_unlink
import persist

app = Flask(__name__)

WORKER_SECRET = os.getenv("WORKER_SECRET", "")

MIN_SECONDS = 30.0
MAX_SECONDS = 35.0
TARGET_SR = 44100   # ⬅️ VAŽNO


def _auth_ok(req) -> bool:
    if not WORKER_SECRET:
        return True
    return req.headers.get("X-Worker-Secret", "") == WORKER_SECRET


@app.get("/")
def root():
    return jsonify({"status": "ok"})


@app.post("/process")
def process():
    if not _auth_ok(request):
        return jsonify({"error": "unauthorized"}), 401

    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400

    f = request.files.get("clip")
    if not f:
        return jsonify({"error": "missing clip"}), 400

    video_path = None
    wav_path = None

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        video_path = tmp.name
        f.save(video_path)
        tmp.close()

        clip_seconds = get_media_duration_seconds(video_path)

        # ⛔ HARD LIMIT
        if clip_seconds < MIN_SECONDS or clip_seconds > MAX_SECONDS:
            return jsonify({
                "error": "invalid_duration",
                "message": f"Clip must be between {MIN_SECONDS} and {MAX_SECONDS} seconds",
                "seconds": clip_seconds
            }), 400

        clip_sha = sha256_file(video_path)

        # 🎧 AUDIO — full clip, no trimming
        wav_path = extract_audio_wav(video_path, target_sr=TARGET_SR)

        # 🔌 ENF
        enf_hash, enf_png, enf_quality, enf_mean, enf_std = extract_enf_from_wav(
            wav_path, mains_hz=50.0
        )

        # 🔊 AUDIO FP
        audio_fp = chromaprint_fp(wav_path)

        # 🎞 VIDEO HASH
        v_phash = video_phash_first_frame(video_path)

        # ⛓ HASH CHAIN
        prev = persist.get_chain_head(user_id)
        payload = {
            "user_id": user_id,
            "clip_sha256": clip_sha,
            "clip_seconds": round(clip_seconds, 2),
            "enf_hash": enf_hash,
            "enf_quality": round(enf_quality, 2),
            "audio_fp": audio_fp[:64],
            "video_phash": v_phash,
        }
        ch = chain_hash(prev, payload)

        proof_id = str(uuid.uuid4())
        png_path = persist.upload_png(user_id, proof_id, enf_png)

        persist.save_result({
            "id": proof_id,
            "user_id": user_id,
            "clip_seconds": clip_seconds,
            "clip_sha256": clip_sha,
            "enf_hash": enf_hash,
            "enf_quality": enf_quality,
            "enf_freq_mean": enf_mean,
            "enf_freq_std": enf_std,
            "audio_fp": audio_fp,
            "audio_fp_algo": "chromaprint",
            "video_phash": v_phash,
            "chain_prev": prev,
            "chain_hash": ch,
            "enf_png_path": png_path
        })

        persist.set_chain_head(user_id, ch)

        return jsonify({
            "ok": True,
            "proof_id": proof_id,
            "enf_quality": enf_quality
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        safe_unlink(video_path)
        safe_unlink(wav_path)
