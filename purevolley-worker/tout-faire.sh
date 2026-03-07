#!/bin/bash
# 🚀 SCRIPT TOUT-EN-UN PUREVOLLEY WORKER
# Exécute ce script sur ton PC Ubuntu et il fait TOUT automatiquement !

set -e  # Arrête le script si erreur

echo "========================================="
echo "🚀 INSTALLATION AUTOMATIQUE PUREVOLLEY"
echo "========================================="
echo "Ce script va installer et configurer ton"
echo "worker IA pour analyser les vidéos de volley."
echo ""
echo "⏱️  Temps estimé : 15-30 minutes"
echo "========================================="

# Demander confirmation
read -p "Continuer ? (o/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    echo "❌ Installation annulée."
    exit 1
fi

# =========================================
# ÉTAPE 1 : Vérifier qu'on est sur Ubuntu
# =========================================
echo ""
echo "🔍 ÉTAPE 1 : Vérification du système..."
if [[ ! -f /etc/os-release ]]; then
    echo "❌ Ce n'est pas Ubuntu. Ce script est pour Ubuntu 22.04."
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    echo "❌ Ce n'est pas Ubuntu. Ce script est pour Ubuntu 22.04."
    exit 1
fi

echo "✅ Système : Ubuntu $VERSION_ID"

# =========================================
# ÉTAPE 2 : Mettre à jour le système
# =========================================
echo ""
echo "🔄 ÉTAPE 2 : Mise à jour du système..."
sudo apt update
sudo apt upgrade -y

# =========================================
# ÉTAPE 3 : Installer ROCm 6.1 pour AMD RX 6600
# =========================================
echo ""
echo "🎮 ÉTAPE 3 : Installation ROCm 6.1 (pour carte graphique AMD)..."
echo "⚠️  Cette étape peut prendre 5-10 minutes."

# Vérifier si ROCm est déjà installé
if ! command -v rocminfo &> /dev/null; then
    echo "📦 Installation de ROCm 6.1..."
    
    # Ajouter le dépôt ROCm
    wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
    echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/6.1 jammy main' | sudo tee /etc/apt/sources.list.d/rocm.list
    
    sudo apt update
    sudo apt install rocm-hip-sdk -y
    
    # Ajouter l'utilisateur au groupe video
    sudo usermod -aG video $USER
    sudo usermod -aG render $USER
    
    echo "✅ ROCm 6.1 installé."
else
    echo "✅ ROCm déjà installé."
fi

# =========================================
# ÉTAPE 4 : Installer Docker
# =========================================
echo ""
echo "🐳 ÉTAPE 4 : Installation de Docker..."

if ! command -v docker &> /dev/null; then
    echo "📦 Installation de Docker..."
    sudo apt install docker.io -y
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Ajouter l'utilisateur au groupe docker
    sudo usermod -aG docker $USER
    
    echo "✅ Docker installé."
else
    echo "✅ Docker déjà installé."
fi

# =========================================
# ÉTAPE 5 : Télécharger le code PureVolley
# =========================================
echo ""
echo "📥 ÉTAPE 5 : Téléchargement du code PureVolley..."

# Vérifier si le dossier existe déjà
if [ -d "purevolley-worker" ]; then
    echo "📁 Dossier déjà présent. Mise à jour..."
    cd purevolley-worker
    git pull
else
    echo "📁 Téléchargement depuis GitHub..."
    git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
    cd volleyball-analyzer/purevolley-worker
fi

# =========================================
# ÉTAPE 6 : Configurer les variables d'environnement
# =========================================
echo ""
echo "⚙️  ÉTAPE 6 : Configuration..."

# Créer le fichier .env si il n'existe pas
if [ ! -f .env ]; then
    echo "📝 Création du fichier de configuration..."
    cp .env.example .env
    
    echo ""
    echo "========================================="
    echo "🔐 CONFIGURATION DES MOTS DE PASSE"
    echo "========================================="
    echo "Il faut maintenant remplir le fichier .env"
    echo "avec tes mots de passe et adresses."
    echo ""
    echo "Ouvre un NOUVEAU terminal et fais :"
    echo "1. cd $(pwd)"
    echo "2. nano .env"
    echo "3. Remplis avec tes informations"
    echo "4. Ctrl+X, puis Y, puis Entrée"
    echo ""
    echo "⚠️  INFOS À TROUVER :"
    echo "- SUPABASE_URL : Sur supabase.com → Settings → API"
    echo "- SUPABASE_SERVICE_ROLE_KEY : Même page"
    echo "- WASABI_ACCESS_KEY : Sur wasabi.com → Access Keys"
    echo "- WASABI_SECRET_KEY : Même page"
    echo ""
    read -p "Quand tu as fini, appuie sur Entrée ici... " -n 1 -r
    echo
else
    echo "✅ Fichier .env déjà configuré."
fi

# =========================================
# ÉTAPE 7 : Tester la carte graphique
# =========================================
echo ""
echo "🧪 ÉTAPE 7 : Test de la carte graphique..."

# Tester ROCm
echo "🔍 Test ROCm..."
if command -v rocminfo &> /dev/null; then
    rocminfo | grep -i "gfx" || true
else
    echo "⚠️  ROCm non détecté."
fi

# Tester avec Python
echo "🔍 Test Python/GPU..."
python3 -c "
try:
    import torch
    print(f'PyTorch version: {torch.__version__}')
    if torch.cuda.is_available():
        print('✅ GPU disponible!')
        print(f'  Carte: {torch.cuda.get_device_name(0)}')
    else:
        print('❌ GPU non disponible')
        print('  Essaye: HSA_OVERRIDE_GFX_VERSION=10.3.0')
except ImportError:
    print('❌ PyTorch non installé')
"

# =========================================
# ÉTAPE 8 : Construire l'image Docker
# =========================================
echo ""
echo "🔨 ÉTAPE 8 : Construction de l'image Docker..."
echo "⚠️  Cette étape peut prendre 10-15 minutes."

# Vérifier Docker
if ! sudo docker info &> /dev/null; then
    echo "❌ Docker ne fonctionne pas. Redémarre l'ordinateur et relance le script."
    exit 1
fi

# Construire l'image
echo "📦 Construction en cours..."
sudo docker build -t purevolley-worker .

# =========================================
# ÉTAPE 9 : Tester l'image Docker
# =========================================
echo ""
echo "🧪 ÉTAPE 9 : Test de l'image Docker..."

echo "🔍 Test GPU dans Docker..."
sudo docker run --rm \
  --env HSA_OVERRIDE_GFX_VERSION=10.3.0 \
  purevolley-worker python check_gpu.py

# =========================================
# ÉTAPE 10 : Installer Coolify
# =========================================
echo ""
echo "🌐 ÉTAPE 10 : Installation de Coolify..."

read -p "Installer Coolify ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "📦 Installation de Coolify..."
    curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
    
    echo ""
    echo "✅ Coolify installé !"
    echo "🌐 Ouvre ton navigateur et va à : http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    echo "📝 Instructions Coolify :"
    echo "1. Crée un compte admin"
    echo "2. Clique sur 'Create New Resource' → 'Application'"
    echo "3. Choisis GitHub et ton projet"
    echo "4. Build Type: Dockerfile"
    echo "5. Dockerfile Path: purevolley-worker/Dockerfile"
    echo "6. Build Context: purevolley-worker"
    echo "7. Dans Docker Settings, ajoute :"
    echo "   Devices: /dev/kfd, /dev/dri"
    echo "   Group Add: video, render"
    echo "8. Copie-colle ton .env dans Environment Variables"
    echo "9. Clique sur Deploy"
else
    echo "⏭️  Coolify non installé."
fi

# =========================================
# ÉTAPE 11 : Démarrer le worker manuellement
# =========================================
echo ""
echo "🚀 ÉTAPE 11 : Démarrer le worker..."

read -p "Démarrer le worker maintenant ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "▶️  Démarrage du worker..."
    
    # Arrêter si déjà en cours
    sudo docker stop purevolley-worker 2>/dev/null || true
    sudo docker rm purevolley-worker 2>/dev/null || true
    
    # Démarrer avec GPU
    sudo docker run -d \
      --name purevolley-worker \
      --restart unless-stopped \
      --device=/dev/kfd \
      --device=/dev/dri \
      --group-add video \
      --group-add render \
      --env-file .env \
      purevolley-worker
    
    echo "✅ Worker démarré !"
    echo "📊 Voir les logs : sudo docker logs -f purevolley-worker"
fi

# =========================================
# ÉTAPE 12 : Vérifications finales
# =========================================
echo ""
echo "✅ ÉTAPE 12 : Vérifications finales..."

echo "🔍 Statut Docker :"
sudo docker ps | grep purevolley-worker || echo "❌ Worker non démarré"

echo ""
echo "🔍 Test de connexion :"
sudo docker exec purevolley-worker python -c "
try:
    from supabase import create_client
    import os
    print('✅ Supabase: Bibliothèque OK')
except:
    print('❌ Supabase: Erreur')

try:
    import boto3
    print('✅ Wasabi: Bibliothèque OK')
except:
    print('❌ Wasabi: Erreur')
"

# =========================================
# FIN
# =========================================
echo ""
echo "========================================="
echo "🎉 INSTALLATION TERMINÉE !"
echo "========================================="
echo ""
echo "✅ CE QUI A ÉTÉ FAIT :"
echo "1. ROCm 6.1 installé (pour GPU AMD)"
echo "2. Docker installé"
echo "3. Code PureVolley téléchargé"
echo "4. Image Docker construite"
echo "5. Worker démarré (si choisi)"
echo "6. Coolify installé (si choisi)"
echo ""
echo "📋 PROCHAINES ÉTAPES :"
echo "1. Vérifie que ton fichier .env est bien rempli"
echo "2. Teste avec : sudo docker logs purevolley-worker"
echo "3. Si erreur GPU : export HSA_OVERRIDE_GFX_VERSION=10.3.0"
echo "4. Pour Coolify : http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "🆘 EN CAS DE PROBLÈME :"
echo "1. Relance le script : bash tout-faire.sh"
echo "2. Vérifie les logs : sudo docker logs purevolley-worker"
echo "3. Demande-moi de l'aide avec le message d'erreur"
echo ""
echo "💡 ASTUCE :"
echo "Redémarre ton ordinateur pour que les groupes (docker, video) soient activés."
echo ""
echo "========================================="
echo "Bonne chance avec ton analyseur de volley ! 🏐"
echo "========================================="