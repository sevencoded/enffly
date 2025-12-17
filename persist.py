import uuid
from datetime import datetime
from utils import supabase_client

def save_proof_and_results(
    user_id,
    enf_hash,
    enf_quality,
    audio_fp,
    video_phash,
    enf_png_bytes,
):
    proof_id = str(uuid.uuid4())

    supabase_client.from_("proofs").insert({
        "id": proof_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    supabase_client.from_("forensic_results").insert({
        "proof_id": proof_id,
        "enf_hash": enf_hash,
        "enf_quality": enf_quality,
        "audio_fp": audio_fp,
        "video_phash": video_phash,
    }).execute()

    supabase_client.storage.from_("main_videos").upload(
        f"{user_id}/{proof_id}_enf.png",
        enf_png_bytes,
        {"content-type": "image/png"},
    )

    return proof_id
