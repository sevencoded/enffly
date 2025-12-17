import os
import tempfile
from flask import Flask, request, jsonify

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from hash_chain import chain_hash
from persist import save_proof_and_results
from utils import require_worker_secret, safe_unlink

app = Flask(__name__)

@app.route("/process", methods=["POST"])
@require_worker_secret
def process():
    audio = request.files.get("audio")
    frames = [
        request.files.get("frame_1"),
        request.files.get("frame_2"),
        request.files.get("frame_3"),
    ]
    user_id = request.form.get("user_id")

    if not audio or not user_id:
        return jsonify({"error": "missing_audio_or_user"}), 400

    # ---- save audio temp ----
    audio_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    audio_path = audio_tmp.name
    audio.save(audio_path)

    try:
        # ---- ENF ----
        enf_hash, enf_png, enf_quality, f_mean, f_std = extract_enf_from_wav(audio_path)

        # ---- Audio FP ----
        audio_fp = extract_audio_fingerprint(audio_path)

        # ---- pHash from frames ----
        frame_hashes = []
        for f in frames:
            if f:
                frame_hashes.append(phash_from_image_bytes(f.read()))

        combined_phash = chain_hash(None, {"frames": frame_hashes}) if frame_hashes else None

        # ---- Persist ----
        proof_id = save_proof_and_results(
            user_id=user_id,
            enf_hash=enf_hash,
            enf_quality=enf_quality,
            audio_fp=audio_fp,
            video_phash=combined_phash,
            enf_png_bytes=enf_png,
        )

        return jsonify({
            "status": "ok",
            "proof_id": proof_id,
            "enf_quality": enf_quality,
        })

    finally:
        safe_unlink(audio_path)
