import tempfile
import subprocess
import traceback
import hashlib
import wave

from flask import Flask, request, jsonify

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from hash_chain import chain_hash
from persist import save_proof_and_results
from utils import require_worker_secret, safe_unlink

app = Flask(__name__)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wav_duration_seconds(path: str) -> float:
    with wave.open(path, "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    return frames / float(rate) if rate else 0.0


@app.route("/process", methods=["POST"])
@require_worker_secret
def process():
    audio = request.files.get("audio")
    user_id = request.form.get("user_id")

    frames = [
        request.files.get("frame_1"),
        request.files.get("frame_2"),
        request.files.get("frame_3"),
    ]

    if not audio or not user_id:
        return jsonify({"error": "missing_audio_or_user"}), 400

    raw_tmp = tempfile.NamedTemporaryFile(delete=False)
    raw_path = raw_tmp.name
    audio.save(raw_path)

    wav_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wav_path = wav_tmp.name

    try:
        # Convert ANY input audio -> WAV PCM
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-ac", "1", "-ar", "44100", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        safe_unlink(raw_path)
        safe_unlink(wav_path)
        return jsonify({
            "error": "audio_conversion_failed",
            "details": e.stderr.decode("utf-8", errors="replace")[:400]
        }), 400

    try:
        # REQUIRED by DB schema
        clip_sha256 = sha256_file(wav_path)
        clip_seconds = wav_duration_seconds(wav_path)

        # ENF
        enf_hash, enf_png, enf_quality, f_mean, f_std = extract_enf_from_wav(wav_path)

        # Audio fingerprint
        audio_fp = extract_audio_fingerprint(wav_path)

        # Frames
        frame_hashes = []
        for f in frames:
            if f:
                frame_hashes.append(phash_from_image_bytes(f.read()))

        video_phash = chain_hash(None, {"frames": frame_hashes}) if frame_hashes else None

        proof_id = save_proof_and_results(
            user_id=user_id,
            clip_seconds=clip_seconds,
            clip_sha256=clip_sha256,
            enf_hash=enf_hash,
            enf_quality=enf_quality,
            enf_freq_mean=f_mean,
            enf_freq_std=f_std,
            audio_fp=audio_fp,
            video_phash=video_phash,
            enf_png_bytes=enf_png,
        )

        return jsonify({
            "status": "ok",
            "proof_id": proof_id,
            "enf_quality": enf_quality,
        }), 200

    except Exception as e:
        return jsonify({
            "error": "processing_failed",
            "details": repr(e),
            "trace": traceback.format_exc().splitlines()[-6:]
        }), 500

    finally:
        safe_unlink(raw_path)
        safe_unlink(wav_path)
