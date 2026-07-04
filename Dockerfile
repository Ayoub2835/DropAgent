FROM python:3.11-slim

# ffmpeg provides both the `ffmpeg` and `ffprobe` binaries used for video
# assembly, subtitle burn-in and multi-platform export. fonts-dejavu-core
# is required by the subtitle/thumbnail renderers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p output assets/music logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
