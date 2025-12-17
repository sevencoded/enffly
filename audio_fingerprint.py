import subprocess


def chromaprint_fp(filepath_wav: str) -> str:
    """
    Compute Chromaprint fingerprint using fpcalc (system tool).
    Requires libchromaprint-tools installed in Docker.
    """
    cmd = ["fpcalc", "-raw", filepath_wav]
    p = subprocess.run(cmd, capture_output=True, text=True)

    if p.returncode != 0:
        raise RuntimeError(f"fpcalc failed: {p.stderr.strip()[:200]}")

    for line in p.stdout.splitlines():
        if line.startswith("FINGERPRINT="):
            return line.split("=", 1)[1].strip()

    raise RuntimeError("fpcalc produced no fingerprint")


# -------------------------------------------------
# PUBLIC API EXPECTED BY app.py
# -------------------------------------------------
def extract_audio_fingerprint(wav_path: str) -> str:
    """
    Wrapper expected by app.py
    """
    return chromaprint_fp(wav_path)
