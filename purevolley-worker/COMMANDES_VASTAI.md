# 🚀 COMMANDES POUR CONFIGURER VAST.AI - TITAN XP

## 📋 **ÉTAPE 1 : CONNEXION SSH**

Ouvre un terminal sur ton PC et colle cette commande :

```bash
ssh -p 63520 root@1.208.108.242
```

**Mot de passe** : Celui affiché sur Vast.ai (dans "Show Web Terminal")

---

## 📋 **ÉTAPE 2 : VÉRIFIER LE SYSTÈME**

Une fois connecté, exécute ces commandes :

### **1. Vérifier Python et pip :**
```bash
python3 --version
pip --version
```

### **2. Vérifier le GPU Titan XP :**
```bash
nvidia-smi
```

**Tu devrais voir :**
- **GPU Name** : TITAN Xp
- **Memory** : 12196MiB (≈12GB)
- **Driver Version** : 535.xxx

---

## 📋 **ÉTAPE 3 : INSTALLER PYTORCH CUDA 13**

```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer PyTorch avec CUDA 12.1 (compatible avec CUDA 13)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Vérifier l'installation
python3 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
```

---

## 📋 **ÉTAPE 4 : CLONER LE REPO**

```bash
# Aller dans /root
cd /root

# Cloner ton repository
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer

# Aller dans le dossier du worker
cd volleyball-analyzer/purevolley-worker
```

---

## 📋 **ÉTAPE 5 : INSTALLER LES DÉPENDANCES**

```bash
# Installer les dépendances du fichier requirements.txt
pip install -r requirements.txt

# Installer OpenCV (nécessaire pour les vidéos)
pip install opencv-python-headless

# Installer boto3 pour AWS S3/Wasabi
pip install boto3

# Installer supabase-py
pip install supabase

# Installer python-dotenv
pip install python-dotenv
```

---

## 📋 **ÉTAPE 6 : CONFIGURER LE FICHIER .env**

```bash
# Copier le fichier exemple
cp .env.example .env

# Éditer le fichier avec nano
nano .env
```

### **Dans nano, remplis ces variables :**
```
SUPABASE_URL=https://ton-url.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb.ta-cle-secrete
WASABI_ACCESS_KEY=ton-access-key
WASABI_SECRET_KEY=ton-secret-key
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
```

### **Pour sauvegarder dans nano :**
1. `Ctrl+X` pour quitter
2. `Y` pour sauvegarder
3. `Entrée` pour confirmer

---

## 📋 **ÉTAPE 7 : TESTER LE GPU AVEC PYTHON**

```bash
# Créer un fichier test_gpu.py
cat > test_gpu.py << 'EOF'
import torch
print("=" * 50)
print("🧪 TEST GPU TITAN XP")
print("=" * 50)
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    device = torch.cuda.current_device()
    print(f"GPU name: {torch.cuda.get_device_name(device)}")
    props = torch.cuda.get_device_properties(device)
    print(f"GPU memory: {props.total_memory / 1e9:.2f} GB")
    print(f"GPU compute capability: {props.major}.{props.minor}")
    
    # Test simple sur GPU
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = x @ y
    print(f"Test matrix multiplication: {z.shape}")
    print("✅ GPU fonctionne correctement!")
else:
    print("❌ GPU non détecté!")
print("=" * 50)
EOF

# Exécuter le test
python3 test_gpu.py
```

---

## 📋 **ÉTAPE 8 : LANCER LE WORKER**

### **Option A : En avant-plan (pour tester)**
```bash
cd /root/volleyball-analyzer/purevolley-worker
python3 worker.py
```

**Tu devrais voir :**
```
🚀 Démarrage du PureVolley Worker
   GPU disponible: True
   PyTorch version: 2.3.0
🔎 Vérification des matchs en attente...
📊 0 match(s) en attente trouvé(s)
😴 Aucun match en attente. Attente de 30 secondes...
```

### **Option B : En arrière-plan (pour production)**
```bash
cd /root/volleyball-analyzer/purevolley-worker
nohup python3 worker.py > worker.log 2>&1 &
```

### **Option C : Avec screen (recommandé)**
```bash
# Installer screen si nécessaire
apt-get update && apt-get install -y screen

# Créer une session screen
screen -S purevolley

# Lancer le worker
cd /root/volleyball-analyzer/purevolley-worker
python3 worker.py

# Pour détacher : Ctrl+A, D
# Pour revenir : screen -r purevolley
```

---

## 📋 **ÉTAPE 9 : VÉRIFIER LES LOGS**

```bash
# Voir les logs en temps réel
tail -f worker.log

# Voir les 50 dernières lignes
tail -50 worker.log

# Chercher des erreurs
grep -i error worker.log
grep -i "gpu disponible" worker.log
```

---

## 📋 **ÉTAPE 10 : TESTER AVEC TON SITE**

### **1. Ouvre ton site Vercel**
- Va sur l'URL de ton site déployé sur Vercel

### **2. Upload une vidéo de test**
- Connecte-toi à ton compte
- Upload une petite vidéo de volley (30 secondes max)

### **3. Vérifie sur le serveur Vast.ai :**
```bash
tail -f worker.log
```

**Tu devrais voir :**
```
🔎 Vérification des matchs en attente...
📊 1 match(s) en attente trouvé(s)
🔍 Traitement du match [ID_DU_MATCH]
📥 Téléchargement depuis S3: bucket=purevolley, key=[CHEMIN_VIDEO]
🎬 Début du traitement pour le match [ID_DU_MATCH]
🤖 Simulation de traitement IA (5 secondes)...
✅ Traitement terminé pour le match [ID_DU_MATCH]
```

---

## 🆘 **DÉPANNAGE**

### **Problème : Connection refused sur SSH**
```bash
# Vérifie le port et l'IP sur Vast.ai
# Le mot de passe change à chaque redémarrage
```

### **Problème : pip non installé**
```bash
apt-get update
apt-get install -y python3-pip
```

### **Problème : git non installé**
```bash
apt-get install -y git
```

### **Problème : GPU non détecté par PyTorch**
```bash
# Vérifie la version de CUDA
nvidia-smi

# Réinstalle PyTorch avec la bonne version CUDA
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### **Problème : Erreur de connexion à Supabase**
```bash
# Vérifie le fichier .env
cat .env

# Teste la connexion
python3 -c "
from supabase import create_client
import os
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
print(f'URL: {url}')
print(f'Key: {key[:20]}...' if key else 'Key: None')
"
```

---

## 📋 **COMMANDES RAPIDES RÉSUMÉ**

```bash
# 1. Connexion
ssh -p 63520 root@1.208.108.242

# 2. Vérification système
nvidia-smi
python3 --version

# 3. Installation
cd /root
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
cd volleyball-analyzer/purevolley-worker
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt opencv-python-headless

# 4. Configuration
cp .env.example .env
nano .env  # Remplis avec tes clés

# 5. Test
python3 test_gpu.py

# 6. Lancement
screen -S purevolley
python3 worker.py
# Ctrl+A, D pour détacher
```

---

## 🎉 **FÉLICITATIONS !**

**Ton worker IA est maintenant :**
- ✅ **Connecté** à ton serveur Vast.ai
- ✅ **Configuré** avec PyTorch CUDA 13
- ✅ **Lié** à Supabase et Wasabi
- ✅ **Prêt** à traiter les vidéos

**Pour vérifier que tout fonctionne :**
1. Upload une vidéo sur ton site
2. Vérifie les logs : `tail -f worker.log`
3. Vérifie que le statut passe de "pending" à "completed"

**Ton site PureVolley est maintenant opérationnel avec GPU !** 🏐