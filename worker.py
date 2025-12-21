# worker.py
import os
import time
import subprocess
from persist import (
    fetch_next_job,
    mark_processing,
    mark_done,
    mark_failed,
)
from utils import safe_unlink


def process_job(job):
    job_id = job["id"]
    audio_path = job["audio_path"]  # PUTANJA NA FLY.IO, ne Supabase

    workdir = f"/tmp/uploads/{job_id}"
    os.makedirs(workdir, exist_ok=True)

    local_audio = audio_path
    enf_audio = os.path.join(workdir, "audio_enf.wav")

    try:
        # 1️⃣ validacija
        if not os.path.exists(local_audio):
            raise FileNotFoundError(f"Audio not found: {local_audio}")

        # 2️⃣ mark processing
        mark_processing(job_id)

        # 3️⃣ ffmpeg ENF prep
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", local_audio,
                "-ac", "1",
                "-ar", "1000",
                "-t", "30",
                enf_audio
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # ⚠️ ovde ide ENF analiza + upload rezultata u main_videos
        # (PNG, trace, spectrogram)

        mark_done(job_id)

    except Exception as e:
        mark_failed(job_id, str(e))
        raise

    finally:
        safe_unlink(enf_audio)
        # ❗ audio se NE briše ovde ako backend još koristi


def main_loop():
    print("Worker started")

    while True:
        job = fetch_next_job()

        if not job:
            time.sleep(2)
            continue

        try:
            process_job(job)
        except Exception as e:
            print("Job failed:", e)
            time.sleep(2)


if __name__ == "__main__":
    main_loop()
