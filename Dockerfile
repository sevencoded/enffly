FROM python:3.11-slim-bullseye

# ---- Environment ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---- System dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libchromaprint-tools \
    libsndfile1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- App directory ----
WORKDIR /app

# ---- Python dependencies ----
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Application code ----
COPY . .

# ---- Runtime ----
EXPOSE 8080
CMD ["gunicorn", "-w", "1", "-k", "gthread", "--threads", "2", "-b", "0.0.0.0:8080", "app:app"]
