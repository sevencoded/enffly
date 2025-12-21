# worker.py
import os
import time
import subprocess
from persist import (
    fetch_next_job,
    mark_processing,
    mark_done,
    mark_failed,
    sb
)
from utils import safe_unlink


UPLOAD_BUCKET = "uploads"


def download_audio(storage_path, local_path):
    bucket = sb.storage.from_("main_videos")
    audio_bytes = bucket.download(storage_path)

    with open(local_path, "wb") as f:
        f.write(audio_bytes)


def process_job(job):
    job_id = job["id"]
    audio_path = job["audio_path"]

    workdir = f"/tmp/uploads/{job_id}"
    os.makedirs(workdir, exist_ok=True)

    local_audio = os.path.join(workdir, "audio.wav")
    enf_audio = os.path.join(workdir, "audio_enf.wav")

    try:
        # 1️⃣ download audio locally
        download_audio(audio_path, local_audio)

        # 2️⃣ mark as processing
        mark_processing(job_id)

        # 3️⃣ run ffmpeg
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
            check=True
        )

        # ⚠️ ovde kasnije ide ENF analiza

        mark_done(job_id)

    except Exception as e:
        mark_failed(job_id, str(e))
        raise

    finally:
        safe_unlink(local_audio)
        safe_unlink(enf_audio)


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
