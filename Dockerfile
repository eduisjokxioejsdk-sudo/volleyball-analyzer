FROM python:3.12-slim

WORKDIR /app

# Install system deps for OpenCV + SSL certificates + git-lfs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 git git-lfs ffmpeg ca-certificates \
    && update-ca-certificates \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps FIRST (cached layer - heaviest step)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone VolleyVision with LFS (model weights are .pt files)
RUN git clone --depth 1 https://github.com/shukkkur/VolleyVision.git /app/VolleyVision \
    && cd /app/VolleyVision && git lfs pull \
    && echo "Model files:" && find /app/VolleyVision -name "best.pt" -exec ls -lh {} \;

# Copy app code (changes often → last layer)
COPY analyze_video.py api_server.py ./

# Update model paths to use /app/VolleyVision
ENV VOLLEYVISION_DIR=/app/VolleyVision
ENV PORT=8080

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "600", "--workers", "1", "--threads", "2", "api_server:app"]
