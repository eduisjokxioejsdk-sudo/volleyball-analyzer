#!/bin/bash
# Script de configuration pour Vast.ai - Titan XP avec CUDA 13

echo "========================================="
echo "🚀 CONFIGURATION VAST.AI - TITAN XP"
echo "========================================="

# 1. Vérifier Python et pip
echo "🔍 Étape 1/6 : Vérification Python et pip..."
python3 --version
pip --version

if ! command -v pip &> /dev/null; then
    echo "📦 Installation de pip..."
    apt-get update && apt-get install -y python3-pip
fi

# 2. Vérifier GPU avec nvidia-smi
echo "🔍 Étape 2/6 : Vérification GPU Titan XP..."
nvidia-smi

# 3. Installer PyTorch avec CUDA 13
echo "🔍 Étape 3/6 : Installation PyTorch CUDA 13..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. Cloner le repo
echo "🔍 Étape 4/6 : Clonage du repository..."
cd /root
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
cd volleyball-analyzer/purevolley-worker

# 5. Installer les autres dépendances
echo "🔍 Étape 5/6 : Installation des dépendances..."
pip install -r requirements.txt

# Installation supplémentaire pour OpenCV
pip install opencv-python-headless

# 6. Configuration du fichier .env
echo "🔍 Étape 6/6 : Configuration .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Fichier .env créé. Édite-le avec tes informations :"
    echo "   nano .env"
    echo ""
    echo "Variables à remplir :"
    echo "SUPABASE_URL=https://ton-url.supabase.co"
    echo "SUPABASE_SERVICE_ROLE_KEY=sb.ta-cle-secrete"
    echo "WASABI_ACCESS_KEY=ton-access-key"
    echo "WASABI_SECRET_KEY=ton-secret-key"
    echo "WASABI_BUCKET=purevolley"
    echo "WASABI_REGION=us-east-1"
    echo "WASABI_ENDPOINT=https://s3.wasabisys.com"
else
    echo "✅ Fichier .env existe déjà"
fi

# 7. Test GPU avec Python
echo "🧪 Test GPU avec Python..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
"

# 8. Lancer le worker en arrière-plan
echo "🚀 Démarrage du worker PureVolley..."
echo "Pour lancer le worker :"
echo "cd /root/volleyball-analyzer/purevolley-worker"
echo "python3 worker.py"
echo ""
echo "Pour lancer en arrière-plan :"
echo "nohup python3 worker.py > worker.log 2>&1 &"
echo ""
echo "Pour voir les logs :"
echo "tail -f worker.log"

echo "========================================="
echo "✅ CONFIGURATION TERMINÉE !"
echo "========================================="
echo ""
echo "📋 Prochaines étapes :"
echo "1. Édite le fichier .env avec tes clés API"
echo "2. Lance le worker avec: python3 worker.py"
echo "3. Vérifie les logs pour confirmer la connexion"
echo "4. Teste avec une vidéo sur ton site"
echo ""
echo "💡 Astuce : Pour garder le worker actif après déconnexion :"
echo "screen -S purevolley"
echo "cd /root/volleyball-analyzer/purevolley-worker"
echo "python3 worker.py"
echo "Ctrl+A, D pour détacher"
echo "screen -r purevolley pour revenir"