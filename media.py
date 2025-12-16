# media.py
import subprocess
import tempfile


def extract_audio_wav(video_path: str, target_sr: int = 44100) -> str:
    """
    Extract FULL audio track from video as mono WAV,
    fixed sample rate, NO trimming.
    Optimized for ENF extraction.
    """
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out.close()

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,

        # ❌ no video
        "-vn",

        # ✅ mono (ENF does not benefit from stereo)
        "-ac", "1",

        # ✅ fixed sample rate (IMPORTANT for Hilbert stability)
        "-ar", str(target_sr),

        # ✅ remove DC + sub-rumble (helps ENF SNR)
        "-af", "highpass=f=20",

        # ✅ uncompressed PCM
        "-c:a", "pcm_s16le",

        out.name
    ]

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    return out.name


def get_media_duration_seconds(path: str) -> float:
    """
    Return media duration in seconds using ffprobe.
    Used to enforce 30–35s HARD LIMIT.
    """
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
