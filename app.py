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

def _auth_ok(req) -> bool:
    if not WORKER_SECRET:
        # allow if unset (dev), but you should set it in production
        return True
    return req.headers.get("X-Worker-Secret", "") == WORKER_SECRET

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/capacity")
def capacity():
    # simple static capacity info; you can wire real concurrency control later
    return jsonify({"busy": False, "retry_after": 2})

@app.post("/process")
def process():
    if not _auth_ok(request):
        return jsonify({"error": "unauthorized"}), 401

    user_id = request.form.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400

    f = request.files.get("clip")
    if not f:
        return jsonify({"error": "missing file field 'clip'"}), 400

    video_path = None
    wav_path = None

    try:
        # save upload to temp file
        suffix = os.path.splitext(f.filename or "")[1] or ".mp4"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        video_path = tmp.name
        f.save(video_path)
        tmp.close()

        clip_sha = sha256_file(video_path)
        clip_seconds = get_media_duration_seconds(video_path)

        # Extract audio wav (mono)
        wav_path = extract_audio_wav(video_path, target_sr=8000)

        # ENF
        enf_hash, enf_png, enf_quality, enf_mean, enf_std = extract_enf_from_wav(wav_path, mains_hz=50.0)

        # Audio fingerprint (Chromaprint)
        audio_fp = chromaprint_fp(wav_path)
        audio_fp_algo = "chromaprint_raw"

        # Video pHash (first frame)
        v_phash = video_phash_first_frame(video_path)

        # Hash chain (per user)
        prev = persist.get_chain_head(user_id)
        chain_payload = {
            "user_id": user_id,
            "clip_sha256": clip_sha,
            "clip_seconds": round(float(clip_seconds or 0.0), 3),
            "enf_hash": enf_hash,
            "enf_quality": round(float(enf_quality), 2),
            "audio_fp": audio_fp[:64],  # store prefix in chain payload to keep it small
            "video_phash": v_phash,
        }
        ch = chain_hash(prev, chain_payload)

        # Optional: upload ENF png to Supabase storage
        proof_id = str(uuid.uuid4())
        png_path = None
        try:
            png_path = persist.upload_png(user_id, proof_id, enf_png)
        except Exception:
            png_path = None

        # Save in Supabase (optional; no-op if env vars missing)
        try:
            persist.save_result({
                "id": proof_id,
                "user_id": user_id,
                "clip_seconds": float(clip_seconds or 0.0),
                "clip_sha256": clip_sha,
                "enf_hash": enf_hash,
                "enf_quality": float(enf_quality),
                "enf_freq_mean": float(enf_mean) if enf_mean == enf_mean else None,
                "enf_freq_std": float(enf_std) if enf_std == enf_std else None,
                "audio_fp": audio_fp,
                "audio_fp_algo": audio_fp_algo,
                "video_phash": v_phash,
                "chain_prev": prev,
                "chain_hash": ch,
                "enf_png_path": png_path
            })
            persist.set_chain_head(user_id, ch)
        except Exception:
            # still return result even if DB fails
            pass

        # Return results (and PNG as base64? keep simple: return png_path + hash)
        return jsonify({
            "ok": True,
            "proof_id": proof_id,
            "user_id": user_id,
            "clip": {
                "sha256": clip_sha,
                "seconds": clip_seconds
            },
            "enf": {
                "hash": enf_hash,
                "quality": enf_quality,
                "freq_mean": enf_mean,
                "freq_std": enf_std,
                "png_supabase_path": png_path
            },
            "audio_fingerprint": {
                "algo": audio_fp_algo,
                "fingerprint": audio_fp
            },
            "video": {
                "phash": v_phash
            },
            "chain": {
                "prev": prev,
                "hash": ch
            }
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        # delete immediately
        safe_unlink(wav_path)
        safe_unlink(video_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
