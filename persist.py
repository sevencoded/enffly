import os
import uuid
from typing import Optional, Dict, Any, Tuple

from supabase import create_client

def _client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def get_chain_head(user_id: str) -> Optional[str]:
    sb = _client()
    if not sb:
        return None
    res = sb.table("forensic_chain_head").select("head_hash").eq("user_id", user_id).limit(1).execute()
    if res.data:
        return res.data[0].get("head_hash")
    return None

def set_chain_head(user_id: str, head_hash: str) -> None:
    sb = _client()
    if not sb:
        return
    # upsert
    sb.table("forensic_chain_head").upsert({
        "user_id": user_id,
        "head_hash": head_hash
    }).execute()

def save_result(row: Dict[str, Any]) -> None:
    sb = _client()
    if not sb:
        return
    sb.table("forensic_results").insert(row).execute()

def upload_png(user_id: str, proof_id: str, png_bytes: bytes) -> Optional[str]:
    """Optional: store ENF png in Supabase Storage bucket 'main_videos' (or change bucket name)."""
    sb = _client()
    if not sb:
        return None
    bucket = os.getenv("SUPABASE_BUCKET", "main_videos")
    path = f"enf/{user_id}/{proof_id}.png"
    sb.storage.from_(bucket).upload(path, png_bytes, {"contentType": "image/png", "upsert": "true"})
    return path
