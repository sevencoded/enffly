# ENF + Audio Fingerprint Forensics API (Fly.io)

This repo is a Dockerized Python API that:
- accepts a short video clip upload (e.g., ~10–30s)
- extracts audio with FFmpeg
- computes:
  - **ENF** (50 Hz) time-series, quality score, and a **real ENF PNG plot**
  - **audio fingerprint** using Chromaprint (`fpcalc`)
  - **video pHash** from a video frame
  - **hash chain** (prev_hash -> new_hash) for tamper-evident linking
- deletes the uploaded media immediately after processing (no unnecessary storage)

## Run locally

```bash
docker build -t enf-api .
docker run --rm -p 8080:8080 -e WORKER_SECRET=dev enf-api
```

Test:
```bash
curl http://localhost:8080/health
```

Process:
```bash
curl -X POST http://localhost:8080/process \
  -H "X-Worker-Secret: dev" \
  -F "user_id=test-user" \
  -F "clip=@/path/to/clip.mp4"
```

## Deploy on Fly.io

```bash
fly launch
fly deploy
fly logs
```

## Optional: Supabase persistence

Set env vars on Fly.io (or locally):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

The API will insert results into table `forensic_results` and maintain a per-user chain in table `forensic_chain_head`.

See `supabase/schema.sql`.

## Security

Use `WORKER_SECRET` and pass it in header `X-Worker-Secret` to protect `/process` from random abuse.
