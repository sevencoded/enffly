import hashlib
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def safe_unlink(path: Optional[str]) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        # don't crash on cleanup
        pass

@dataclass
class EnfResult:
    enf_hash: str
    quality: float
    f_mean: float
    f_std: float
    png_bytes: bytes

@dataclass
class ForensicResult:
    clip_sha256: str
    clip_seconds: float
    enf: EnfResult
    audio_fp: str
    audio_fp_algo: str
    video_phash: Optional[str]
    chain_prev: Optional[str]
    chain_hash: str
    enf_png_path: Optional[str] = None
