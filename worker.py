# worker.py
import os
import time
import subprocess
from persist import fetch_next_job, mark_processing, mark_done, mark_failed
from utils import safe_unlink


def process_job(job):
    job_id = job["id"]
    audio_path = job["audio_path"]  # LOKALNA PUTANJA NA FLY.IO

    workdir = os.path.dirname(audio_path)
    enf_audio = os.path.join(workdir, "audio_enf.wav")

    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)

        mark_processing(job_id)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", audio_path,
                "-ac", "1",
                "-ar", "1000",
                "-t", "30",
                enf_audio
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # ⬇⬇⬇
        # OVDE IDE:
        # - ENF analiza
        # - generisanje PNG / trace / spectrogram
        # - upload SAMO tih fajlova u Supabase bucket `main_videos`
        # - upis forensic_results

        mark_done(job_id)

    except Exception as e:
        mark_failed(job_id, str(e))
        raise

    finally:
        safe_unlink(enf_audio)
        # audio se briše KASNIJE (cron / cleanup), ne ovde


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
