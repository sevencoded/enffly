import uuid

from utils import supabase_client


def _ensure_upload_ok(resp, label: str, path: str):
    """
    supabase-py upload često NE baca exception,
    nego vraća objekat/dict sa error/statusCode.
    Ovo forsira fail kad upload ne uspe.
    """
    err = None
    status = None

    if isinstance(resp, dict):
        err = resp.get("error") or resp.get("message")
        status = resp.get("statusCode") or resp.get("status") or resp.get("code")
    else:
        err = getattr(resp, "error", None)
        status = getattr(resp, "status_code", None) or getattr(resp, "status", None)

    if err:
        raise RuntimeError(
            f"{label} upload failed for {path}: {err} (status={status})"
        )


def save_proof_and_results(
    *,
    user_id: str,
    proof_name: str,              # ← DODATO
    clip_seconds: float,
    clip_sha256: str,
    enf_hash: str,
    enf_quality: float,
    enf_freq_mean: float,
    enf_freq_std: float,
    audio_fp: str | None,
    video_phash: str | None,
    enf_trace_png_bytes: bytes,
    enf_spectrogram_png_bytes: bytes,
):
    proof_id = str(uuid.uuid4())

    # ---------------- GUARDS ----------------
    if not proof_name or len(proof_name.strip()) < 2:
        raise ValueError("Invalid proof name")

    proof_name = proof_name.strip()

    if not enf_trace_png_bytes or len(enf_trace_png_bytes) < 100:
        raise ValueError("ENF trace PNG bytes missing/too small")
    if not enf_spectrogram_png_bytes or len(enf_spectrogram_png_bytes) < 100:
        raise ValueError("ENF spectrogram PNG bytes missing/too small")

    # ---------------- PREV HASH ----------------
    head = (
        supabase_client
        .from_("forensic_chain_head")
        .select("head_hash")
        .eq("user_id", user_id)
        .execute()
    )
    prev_hash = head.data[0]["head_hash"] if head.data else None

    trace_path = f"{user_id}/{proof_id}_enf_trace.png"
    spec_path = f"{user_id}/{proof_id}_enf_spectrogram.png"

    # ---------------- INSERT METADATA ----------------
    try:
        supabase_client.from_("forensic_results").insert({
            "id": proof_id,
            "user_id": user_id,
            "name": proof_name,          # ← KLJUČNO
            "clip_seconds": clip_seconds,
            "clip_sha256": clip_sha256,
            "enf_hash": enf_hash,
            "enf_quality": enf_quality,
            "enf_freq_mean": enf_freq_mean,
            "enf_freq_std": enf_freq_std,
            "audio_fp": audio_fp,
            "audio_fp_algo": "chromaprint",
            "video_phash": video_phash,
            "chain_prev": prev_hash,
            "chain_hash": clip_sha256,
            "enf_trace_path": trace_path,
            "enf_spectrogram_path": spec_path,
        }).execute()
    except Exception as e:
        msg = str(e)
        if "forensic_results_user_name_unique" in msg:
            raise ValueError("duplicate_proof_name")
        raise

    # ---------------- UPLOAD TRACE ----------------
    r1 = supabase_client.storage.from_("main_videos").upload(
        trace_path,
        enf_trace_png_bytes,
        {"content-type": "image/png", "upsert": "true"},
    )
    _ensure_upload_ok(r1, "ENF TRACE", trace_path)

    # ---------------- UPLOAD SPECTROGRAM ----------------
    r2 = supabase_client.storage.from_("main_videos").upload(
        spec_path,
        enf_spectrogram_png_bytes,
        {"content-type": "image/png", "upsert": "true"},
    )
    _ensure_upload_ok(r2, "ENF SPECTROGRAM", spec_path)

    # ---------------- UPDATE CHAIN HEAD ----------------
    supabase_client.from_("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": clip_sha256,
    }).execute()

    return proof_id
