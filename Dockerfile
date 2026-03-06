FROM python:3.11-slim

# Dépendances système pour OpenCV et git (pour pip install from github)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source (ml_manager + scripts)
COPY ml_manager/ ./ml_manager/
COPY analyze_video.py .
COPY api_server.py .

# Port exposé pour l'API
EXPOSE 8000

# Lancer le serveur API
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
