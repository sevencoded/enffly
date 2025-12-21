import hashlib
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def persist_result(job, enf, audio_fp, phashes):
    user_id = job["user_id"]

    head = supabase.table("forensic_chain_head") \
        .select("head_hash") \
        .eq("user_id", user_id) \
        .execute()

    prev = head.data[0]["head_hash"] if head.data else None
    chain = hashlib.sha256(
        (str(prev) + enf["hash"]).encode()
    ).hexdigest()

    supabase.table("forensic_results").insert({
        "id": job["id"],
        "user_id": user_id,
        "clip_sha256": enf["hash"],
        "enf_hash": enf["hash"],
        "audio_fp": audio_fp,
        "video_phash": ",".join(phashes),
        "chain_prev": prev,
        "chain_hash": chain,
        "enf_png_path": enf["png_supabase_path"],
        "name": "ENF Proof"
    }).execute()

    supabase.table("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": chain
    }).execute()
