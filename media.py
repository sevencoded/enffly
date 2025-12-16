import os
import subprocess
import tempfile
from typing import Tuple

def extract_audio_wav(video_path: str, target_sr: int = 8000) -> str:
    """Extract mono WAV from video using ffmpeg to a temp file."""
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out.close()
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", str(target_sr),
        "-f", "wav",
        out.name
    ]
    # silence logs unless error
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out.name

def get_media_duration_seconds(path: str) -> float:
    """Return duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return 0.0
    try:
        return float(p.stdout.strip())
    except Exception:
        return 0.0
