FROM python:3.12-slim

WORKDIR /app

# Install system deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Clone VolleyVision (only the model weights)
RUN git clone --depth 1 https://github.com/shukkkur/VolleyVision.git /app/VolleyVision

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt flask flask-cors gunicorn

# Copy app code
COPY analyze_video.py api_server.py ./

# Update model paths to use /app/VolleyVision
ENV VOLLEYVISION_DIR=/app/VolleyVision
ENV PORT=8080

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "600", "--workers", "1", "--threads", "2", "api_server:app"]
