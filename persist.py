import uuid

from utils import supabase_client


def save_proof_and_results(
    *,
    user_id: str,
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
    # -------------------------------------------------
    # 1) GENERATE PROOF ID
    # -------------------------------------------------
    proof_id = str(uuid.uuid4())

    # -------------------------------------------------
    # 2) GET PREVIOUS CHAIN HEAD
    # -------------------------------------------------
    head = (
        supabase_client
        .from_("forensic_chain_head")
        .select("head_hash")
        .eq("user_id", user_id)
        .execute()
    )

    prev_hash = head.data[0]["head_hash"] if head.data else None

    # -------------------------------------------------
    # 3) INSERT FORENSIC RESULT (METADATA ONLY)
    # -------------------------------------------------
    supabase_client.from_("forensic_results").insert({
        "id": proof_id,
        "user_id": user_id,
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
        "enf_trace_path": f"{user_id}/{proof_id}_enf_trace.png",
        "enf_spectrogram_path": f"{user_id}/{proof_id}_enf_spectrogram.png",
    }).execute()

    # -------------------------------------------------
    # 4) UPLOAD ENF TRACE (GRAPH)
    # -------------------------------------------------
    supabase_client.storage.from_("main_videos").upload(
        f"{user_id}/{proof_id}_enf_trace.png",
        enf_trace_png_bytes,
        {"content-type": "image/png"},
    )

    # -------------------------------------------------
    # 5) UPLOAD RAW ENF SPECTROGRAM (CRITICAL FIX)
    # -------------------------------------------------
    supabase_client.storage.from_("main_videos").upload(
        f"{user_id}/{proof_id}_enf_spectrogram.png",
        enf_spectrogram_png_bytes,
        {"content-type": "image/png"},
    )

    # -------------------------------------------------
    # 6) UPDATE CHAIN HEAD
    # -------------------------------------------------
    supabase_client.from_("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": clip_sha256,
    }).execute()

    return proof_id
