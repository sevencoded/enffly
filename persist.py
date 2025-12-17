import uuid
from datetime import datetime
from utils import supabase_client
from hash_chain import chain_hash


def save_proof_and_results(
    user_id,
    enf_hash,
    enf_quality,
    enf_freq_mean,
    enf_freq_std,
    audio_fp,
    video_phash,
    enf_png_bytes,
):
    proof_id = str(uuid.uuid4())

    # ---- read previous chain head ----
    prev = (
        supabase_client
        .from_("forensic_chain_head")
        .select("head_hash")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    prev_hash = prev.data["head_hash"] if prev.data else None

    # ---- build chain payload ----
    payload = {
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "audio_fp": audio_fp,
        "video_phash": video_phash,
    }

    current_chain_hash = chain_hash(prev_hash, payload)

    # ---- insert forensic result ----
    supabase_client.from_("forensic_results").insert({
        "id": proof_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
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

    # ---- upsert chain head ----
    supabase_client.from_("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": current_chain_hash,
        "updated_at": datetime.utcnow().isoformat(),
    }).execute()

    # ---- upload ENF PNG ----
    supabase_client.storage.from_("main_videos").upload(
        f"{user_id}/{proof_id}_enf.png",
        enf_png_bytes,
        {"content-type": "image/png"},
    )

    return proof_id
