# PureVolley Worker Dockerfile
# Basé sur ROCm 6.1 pour AMD Radeon RX 6600
# HSA_OVERRIDE_GFX_VERSION=10.3.0 requis pour la RX 6600

FROM rocm/dev-ubuntu-22.04:6.1

# Variables d'environnement pour la RX 6600
ENV HSA_OVERRIDE_GFX_VERSION=10.3.0
ENV ROCM_PATH=/opt/rocm
ENV PATH=$ROCM_PATH/bin:$PATH
ENV LD_LIBRARY_PATH=$ROCM_PATH/lib:$LD_LIBRARY_PATH

# Mise à jour des paquets système
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python avec ROCm 6.1
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Installation de PyTorch avec ROCm 6.1 (explicitement)
RUN pip3 install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/rocm6.1 \
    torch torchvision torchaudio

# Copie du code source
COPY . .

# Création d'un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 worker && \
    chown -R worker:worker /app
USER worker

# Vérification de la disponibilité GPU
RUN python3 -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'ROCm available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"No GPU\"}')"

# Point d'entrée par défaut
CMD ["python3", "worker.py"]