#!/bin/bash
# Script d'installation automatique pour PureVolley Worker sur Coolify
# Ce script prépare tous les fichiers de configuration pour un déploiement facile

set -e

echo "========================================="
echo "PureVolley Worker - Setup Coolify"
echo "========================================="

# Créer le répertoire de configuration
CONFIG_DIR="./coolify-deploy"
mkdir -p "$CONFIG_DIR"

echo "📁 Création des fichiers de configuration Coolify..."

# 1. Fichier docker-compose.yml optimisé pour Coolify
cat > "$CONFIG_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  purevolley-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: purevolley-worker
    restart: unless-stopped
    
    # Configuration GPU pour AMD RX 6600 avec ROCm 6.1
    devices:
      - /dev/kfd
      - /dev/dri
    
    # Groupes nécessaires pour l'accès GPU
    group_add:
      - video
      - render
    
    # Variables d'environnement (à remplacer dans Coolify)
    environment:
      # GPU Configuration
      - HSA_OVERRIDE_GFX_VERSION=10.3.0
      - ROCM_PATH=/opt/rocm
      
      # Supabase Configuration
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      
      # Wasabi S3 Configuration
      - WASABI_ACCESS_KEY=${WASABI_ACCESS_KEY}
      - WASABI_SECRET_KEY=${WASABI_SECRET_KEY}
      - WASABI_BUCKET=${WASABI_BUCKET:-purevolley}
      - WASABI_REGION=${WASABI_REGION:-us-east-1}
      - WASABI_ENDPOINT=${WASABI_ENDPOINT:-https://s3.wasabisys.com}
      
      # Worker Configuration
      - POLL_INTERVAL_SECONDS=${POLL_INTERVAL_SECONDS:-30}
      - MAX_RETRIES=${MAX_RETRIES:-3}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    
    # Health check
    healthcheck:
      test: ["CMD", "python", "check_gpu.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# 2. Fichier .env.example pour Coolify
cat > "$CONFIG_DIR/.env.example" << 'EOF'
# PureVolley Worker - Variables d'environnement pour Coolify
# Copier en .env et remplir avec vos valeurs

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Wasabi S3 Configuration
WASABI_ACCESS_KEY=your-wasabi-access-key
WASABI_SECRET_KEY=your-wasabi-secret-key
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com

# GPU Configuration (pour AMD RX 6600)
HSA_OVERRIDE_GFX_VERSION=10.3.0
ROCM_PATH=/opt/rocm

# Worker Configuration
POLL_INTERVAL_SECONDS=30
MAX_RETRIES=3
LOG_LEVEL=INFO
EOF

# 3. Instructions de déploiement
cat > "$CONFIG_DIR/DEPLOY.md" << 'EOF'
# Déploiement PureVolley Worker sur Coolify

## 📋 Prérequis
- Serveur Ubuntu 22.04 avec AMD RX 6600
- ROCm 6.1 installé sur l'hôte
- Coolify installé et accessible (IP:8000)

## 🚀 Déploiement en 5 étapes

### 1. Dans Coolify (votre-IP:8000)
- Cliquez sur "Create New Resource"
- Sélectionnez "Application"
- Choisissez votre repository GitHub

### 2. Configuration du build
- **Build Type**: Dockerfile
- **Dockerfile Path**: `purevolley-worker/Dockerfile`
- **Build Context**: `purevolley-worker`

### 3. Configuration Docker (CRITIQUE pour GPU)
Dans les paramètres Docker avancés, ajoutez :

```yaml
devices:
  - /dev/kfd
  - /dev/dri

group_add:
  - video
  - render

environment:
  - HSA_OVERRIDE_GFX_VERSION=10.3.0
```

### 4. Variables d'environnement
Configurez les variables suivantes :

| Variable | Valeur exemple |
|----------|----------------|
| `SUPABASE_URL` | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbGciOiJIUzI1NiIs...` |
| `WASABI_ACCESS_KEY` | `ABCDEFGHIJKLMNOPQRST` |
| `WASABI_SECRET_KEY` | `abcdefghijklmnopqrstuvwxyz0123456789ABCD` |
| `WASABI_BUCKET` | `purevolley` |
| `WASABI_REGION` | `us-east-1` |
| `WASABI_ENDPOINT` | `https://s3.wasabisys.com` |
| `HSA_OVERRIDE_GFX_VERSION` | `10.3.0` |

### 5. Déploiement
- Cliquez sur "Deploy"
- Surveillez les logs

## ✅ Vérification du succès

Dans les logs Coolify, cherchez :

```
✅ GPU disponible: AMD Radeon RX 6600
✅ Connexion à Supabase établie
✅ Connexion à Wasabi S3 établie
```

## 🐛 Dépannage

### GPU non détecté
1. Vérifiez que ROCm 6.1 est installé sur l'hôte
2. Vérifiez les devices `/dev/kfd` et `/dev/dri`
3. Vérifiez `HSA_OVERRIDE_GFX_VERSION=10.3.0`

### Erreur Supabase
1. Vérifiez les permissions du service role
2. Vérifiez que la table `matches` existe

### Erreur Wasabi
1. Vérifiez les permissions du bucket
2. Vérifiez les clés d'accès
EOF

# 4. Script de vérification post-déploiement
cat > "$CONFIG_DIR/verify-deployment.sh" << 'EOF'
#!/bin/bash
# Script de vérification post-déploiement Coolify

echo "🔍 Vérification du déploiement PureVolley Worker..."

# Vérifier les variables d'environnement
echo "1. Variables d'environnement:"
env | grep -E "(SUPABASE|WASABI|HSA|ROCM)" | sort

# Vérifier les devices GPU
echo -e "\n2. Devices GPU:"
if [ -e /dev/kfd ]; then
    echo "   ✅ /dev/kfd présent"
else
    echo "   ❌ /dev/kfd absent"
fi

if [ -e /dev/dri ]; then
    echo "   ✅ /dev/dri présent"
    ls -la /dev/dri/
else
    echo "   ❌ /dev/dri absent"
fi

# Vérifier les groupes
echo -e "\n3. Groupes de l'utilisateur:"
groups

# Tester PyTorch
echo -e "\n4. Test PyTorch GPU:"
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'GPU available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
"

echo -e "\n🎉 Vérification terminée!"
EOF

chmod +x "$CONFIG_DIR/verify-deployment.sh"

# Copier les fichiers essentiels
cp Dockerfile "$CONFIG_DIR/"
cp requirements.txt "$CONFIG_DIR/"
cp worker.py "$CONFIG_DIR/"
cp check_gpu.py "$CONFIG_DIR/"
cp .env.example "$CONFIG_DIR/"

echo "✅ Configuration Coolify créée dans: $CONFIG_DIR"
echo ""
echo "📋 Étapes suivantes:"
echo "1. cd $CONFIG_DIR"
echo "2. Remplir le fichier .env avec vos valeurs"
echo "3. Suivre les instructions dans DEPLOY.md"
echo "4. Déployer sur Coolify"
echo ""
echo "🚀 Votre PureVolley Worker est prêt pour le déploiement!"