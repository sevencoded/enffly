import uuid
from datetime import datetime
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
    enf_png_bytes: bytes,
):
    proof_id = str(uuid.uuid4())

    head = supabase_client.from_("forensic_chain_head") \
        .select("head_hash") \
        .eq("user_id", user_id) \
        .execute()

    prev_hash = head.data[0]["head_hash"] if head.data else None
    current_chain_hash = clip_sha256

    supabase_client.from_("forensic_results").insert({
        "id": proof_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),

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
        "chain_hash": current_chain_hash,

        "enf_png_path": f"{user_id}/{proof_id}_enf.png",
    }).execute()

    supabase_client.from_("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": current_chain_hash,
        "updated_at": datetime.utcnow().isoformat(),
    }).execute()

    supabase_client.storage.from_("main_videos").upload(
        f"{user_id}/{proof_id}_enf.png",
        enf_png_bytes,
        {"content-type": "image/png"},
    )

    return proof_id
