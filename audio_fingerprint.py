import subprocess
from typing import Optional

def chromaprint_fp(filepath_wav: str) -> str:
    """Compute Chromaprint fingerprint using fpcalc (installed via chromaprint package)."""
    # fpcalc outputs lines like:
    # DURATION=12
    # FINGERPRINT=...
    cmd = ["fpcalc", "-raw", filepath_wav]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"fpcalc failed: {p.stderr.strip()[:200]}")
    fp = None
    for line in p.stdout.splitlines():
        if line.startswith("FINGERPRINT="):
            fp = line.split("=", 1)[1].strip()
            break
    if not fp:
        raise RuntimeError("fpcalc produced no fingerprint")
    return fp
