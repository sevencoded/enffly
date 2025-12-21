# worker.py
import os
import time
import traceback
import subprocess
from datetime import datetime, timedelta

from enf import extract_enf_from_wav
from audio_fingerprint import extract_audio_fingerprint
from video_phash import phash_from_image_bytes
from hash_chain import chain_hash
from persist import (
    fetch_next_job,
    mark_processing,
    mark_done,
    mark_failed,
)
from utils import safe_unlink

MAX_ATTEMPTS = 3
MAX_PROCESSING_TIME = timedelta(hours=2)

FFMPEG = "ffmpeg"


def process_job(job):
    job_id = job["job_id"]
    audio_path = job["audio_path"]
    frame_paths = job["frame_paths"]

    enf_wav = audio_path.replace(".wav", "_enf.wav")

    try:
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-i", audio_path,
                "-ac", "1",
                "-ar", "1000",
                "-t", "30",
                enf_wav
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        enf_metrics, enf_png = extract_enf_from_wav(enf_wav)
        audio_fp = extract_audio_fingerprint(enf_wav)

        image_phashes = []
        for p in frame_paths:
            with open(p, "rb") as f:
                image_phashes.append(phash_from_image_bytes(f.read()))

        final_hash = chain_hash(
            enf_metrics,
            audio_fp,
            image_phashes
        )

        mark_done(
            job_id=job_id,
            result_hash=final_hash,
            enf_metrics=enf_metrics,
            audio_fp=audio_fp,
            image_phashes=image_phashes,
        )

    finally:
        safe_unlink(enf_wav)
        safe_unlink(audio_path)
        for p in frame_paths:
            safe_unlink(p)


def main_loop():
    print("Worker started")

    while True:
        job = fetch_next_job()

        if not job:
            time.sleep(2)
            continue

        job_id = job["job_id"]

        try:
            mark_processing(job_id)

            started = datetime.utcnow()
            process_job(job)

            duration = datetime.utcnow() - started
            print(f"[OK] job {job_id} in {duration}")

        except Exception:
            traceback.print_exc()

            if job["attempt_count"] + 1 >= MAX_ATTEMPTS:
                mark_failed(job_id, "max_attempts_exceeded")
            else:
                mark_failed(job_id, "processing_error")

        time.sleep(0.2)


if __name__ == "__main__":
    main_loop()
