# 🚀 GUIDE : HÉBERGER PUREVOLLEY SUR RUNPOD/VAST.AI (PAY-PER-USE)

## 🎯 **Objectif :**
Déployer ton worker IA sur un VPS avec GPU partagé pour ~5-15€/mois selon l'utilisation.

---

## 📊 **COMPARAISON DES PLATEFORMES**

### **RunPod.io** (recommandé)
- ✅ **Pay-per-second** (0.79€/heure pour RTX 4090)
- ✅ **Déploiement Docker simple**
- ✅ **Interface web intuitive**
- ✅ **Stockage persistant**
- ✅ **Ports publics gratuits**

### **Vast.ai**
- ✅ **Encore moins cher** (marché spot)
- ✅ **Plus de choix GPU**
- ❌ **Interface moins intuitive**
- ❌ **Configuration plus complexe**

### **Prix estimés :**
- **RunPod RTX 4090** : 0.79€/heure → ~5-10€/mois pour usage occasionnel
- **Vast.ai RTX 4090** : 0.45-0.65€/heure → ~3-8€/mois
- **Stockage** : 0.25€/GB/mois (10GB = 2.5€/mois)

**Budget total : 5-15€/mois** selon l'utilisation

---

## 📋 **ÉTAPE 1 : PRÉPARATION DU DOCKERFILE**

Ton `Dockerfile` est déjà prêt dans `purevolley-worker/Dockerfile`. Il utilise `rocm/dev-ubuntu-22.04:6.1` pour AMD RX 6600.

**MAIS** pour RunPod/Vast.ai (GPU NVIDIA), tu as besoin d'une version différente :

### **Créer un nouveau Dockerfile pour NVIDIA :**
```dockerfile
# Dockerfile.nvidia
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Variables d'environnement
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Installation de PyTorch avec CUDA 12.1
RUN pip3 install --no-cache-dir \
    torch==2.3.0 \
    torchvision==0.18.0 \
    torchaudio==2.3.0 \
    --index-url https://download.pytorch.org/whl/cu121

# Installation des autres dépendances
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copie du code
COPY . /app
WORKDIR /app

# Commande par défaut
CMD ["python3", "worker.py"]
```

---

## 📋 **ÉTAPE 2 : CONSTRUIRE ET PUSHER L'IMAGE DOCKER**

### **1. Créer un compte Docker Hub**
- Va sur [hub.docker.com](https://hub.docker.com)
- Crée un compte gratuit
- Note ton nom d'utilisateur (ex: `tonnom`)

### **2. Construire l'image localement :**
```bash
cd ~/Documents/purevolley-worker
docker build -f Dockerfile.nvidia -t tonnom/purevolley-worker:nvidia .
```

### **3. Tagger et pousser :**
```bash
docker tag tonnom/purevolley-worker:nvidia tonnom/purevolley-worker:nvidia-latest
docker push tonnom/purevolley-worker:nvidia-latest
```

---

## 📋 **ÉTAPE 3 : DÉPLOIEMENT SUR RUNPOD**

### **1. Créer un compte RunPod**
- Va sur [runpod.io](https://runpod.io)
- Inscris-toi (Google/GitHub)
- Ajoute des crédits (10€ pour commencer)

### **2. Créer un template :**
1. **Community Templates** → **Create New Template**
2. **Nom** : `purevolley-worker`
3. **Image Docker** : `tonnom/purevolley-worker:nvidia-latest`
4. **Container Disk** : 10GB
5. **Ports** :
   - `22` (SSH - optionnel)
   - `8000` (pour API future)
6. **Environment Variables** :
   ```
   SUPABASE_URL=https://ton-url.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=sb.ta-cle-secrete
   WASABI_ACCESS_KEY=ton-access-key
   WASABI_SECRET_KEY=ton-secret-key
   WASABI_BUCKET=purevolley
   WASABI_REGION=us-east-1
   WASABI_ENDPOINT=https://s3.wasabisys.com
   ```
7. **Commande** : `python3 worker.py`

### **3. Démarrer un pod :**
1. **Deploy** → **Secure Cloud**
2. **GPU Type** : RTX 4090 (ou 3080 pour moins cher)
3. **Template** : `purevolley-worker`
4. **Clique sur "Deploy"**

**Coût** : 0.79€/heure pour RTX 4090

---

## 📋 **ÉTAPE 4 : DÉPLOIEMENT SUR VAST.AI (MOINS CHER)**

### **1. Créer un compte Vast.ai**
- Va sur [vast.ai](https://vast.ai)
- Inscris-toi
- Ajoute des crédits (5€ pour commencer)

### **2. Chercher une instance :**
1. **Rent** → **Search Offers**
2. **Filtres** :
   - **GPU** : RTX 4090 ou 3080
   - **Disk Space** : ≥20GB
   - **Internet** : ✅
   - **Price** : < 0.70€/heure
3. **Clique sur "Rent"**

### **3. Configurer l'instance :**
1. **Image** : `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
2. **Jupyter** : Désactivé (on utilise Docker)
3. **Ports** : `22` (SSH)
4. **Clique sur "Launch"**

### **4. Se connecter en SSH :**
```bash
# Copie la commande SSH depuis Vast.ai
ssh -p PORT root@IP_ADRESSE

# Mot de passe : celui affiché sur Vast.ai
```

### **5. Installer Docker et déployer :**
```bash
# Sur l'instance Vast.ai
apt update && apt install docker.io -y

# Télécharger ton code
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
cd volleyball-analyzer/purevolley-worker

# Créer .env
nano .env
# Colle tes variables d'environnement

# Construire et exécuter
docker build -f Dockerfile.nvidia -t purevolley-worker .
docker run -d --name purevolley-worker --gpus all purevolley-worker

# Vérifier
docker logs purevolley-worker
```

---

## 📋 **ÉTAPE 5 : CONFIGURER LE FRONTEND (Vercel)**

### **Ton frontend React peut être hébergé GRATUITEMENT sur Vercel :**

### **1. Créer un compte Vercel**
- Va sur [vercel.com](https://vercel.com)
- Connecte-toi avec GitHub

### **2. Importer ton projet :**
1. **New Project** → **Import Git Repository**
2. Sélectionne ton repo `volleyball-analyzer`
3. **Framework Preset** : Vite
4. **Root Directory** : `/` (racine)
5. **Build Command** : `npm run build`
6. **Output Directory** : `dist`
7. **Clique sur "Deploy"**

### **3. Configurer les variables d'environnement :**
Dans Vercel → Project → Settings → Environment Variables :
```
VITE_SUPABASE_URL=https://ton-url.supabase.co
VITE_SUPABASE_ANON_KEY=ton-anon-key
VITE_WASABI_BUCKET=purevolley
```

**✅ Frontend GRATUIT sur Vercel !**

---

## 📋 **ÉTAPE 6 : ARCHITECTURE FINALE**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   UTILISATEUR   │───▶│    FRONTEND     │───▶│    SUPABASE     │
│                 │    │    (Vercel)     │    │    (Database)   │
│                 │    │     GRATUIT     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   WASABI S3     │◀───│   WORKER IA     │◀───│   MATCH PENDING │
│   (Stockage)    │    │   (RunPod)      │    │                 │
│                 │    │   5-15€/mois    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🆘 **DÉPANNAGE**

### **Problème : GPU non détecté sur RunPod**
```bash
# Dans le terminal RunPod
docker exec -it CONTAINER_ID bash
python3 -c "import torch; print(torch.cuda.is_available())"
```

**Solution :** Vérifie que tu utilises `Dockerfile.nvidia` et pas le fichier ROCm.

### **Problème : Connexion à Supabase échoue**
```bash
# Vérifie les variables d'environnement
docker exec CONTAINER_ID env | grep SUPABASE
```

**Solution :** Mets à jour les variables dans le template RunPod.

### **Problème : Vidéo non téléchargée depuis Wasabi**
```bash
# Teste la connexion S3
docker exec CONTAINER_ID python3 -c "
import boto3, os
s3 = boto3.client('s3',
  endpoint_url=os.getenv('WASABI_ENDPOINT'),
  aws_access_key_id=os.getenv('WASABI_ACCESS_KEY'),
  aws_secret_access_key=os.getenv('WASABI_SECRET_KEY')
)
print(s3.list_buckets())
"
```

---

## 💰 **ESTIMATION DES COÛTS**

### **Scenario 1 : Usage léger (test)**
- **RunPod RTX 4090** : 2 heures/jour × 30 jours = 60 heures
- **Coût** : 60h × 0.79€ = **47.40€/mois** (trop cher)

### **Scenario 2 : Vast.ai + optimisation**
- **Vast.ai RTX 3080** : 0.35€/heure
- **Usage** : 1 heure/jour × 30 jours = 30 heures
- **Coût** : 30h × 0.35€ = **10.50€/mois** ✅
- **Stockage** : 10GB × 0.25€ = **2.50€/mois**
- **Total** : **~13€/mois** ✅

### **Scenario 3 : CPU seulement (pas de GPU)**
- **DigitalOcean** : 4GB RAM = 6€/mois
- **Mais** : traitement vidéo très lent

**Je recommande le Scenario 2 (Vast.ai)**

---

## 🎯 **RÉSUMÉ DES ÉTAPES**

### **Option A : RunPod (plus simple)**
1. ✅ Créer `Dockerfile.nvidia`
2. ✅ Pousser sur Docker Hub
3. ✅ Créer template RunPod
4. ✅ Démarrer pod
5. ✅ Héberger frontend sur Vercel

### **Option B : Vast.ai (moins cher)**
1. ✅ Créer `Dockerfile.nvidia`
2. ✅ Louer instance Vast.ai
3. ✅ SSH + Docker manuel
4. ✅ Démarrer worker
5. ✅ Héberger frontend sur Vercel

---

## 📞 **SUPPORT**

### **Si bloqué sur RunPod :**
1. **Console** → **Logs** pour voir les erreurs
2. **Terminal** pour debug
3. **Documentation** : [docs.runpod.io](https://docs.runpod.io)

### **Si bloqué sur Vast.ai :**
1. **SSH** dans l'instance
2. `docker logs purevolley-worker`
3. **Support** : support@vast.ai

### **Alternative d'urgence :**
Utilise **CPU seulement** sur DigitalOcean (6€/mois) le temps que ton PC Ubuntu soit prêt.

---

## 🎉 **BON DÉPLOIEMENT !**

**Avec cette solution :**
- ✅ **Frontend** : GRATUIT sur Vercel
- ✅ **Backend IA** : 5-15€/mois sur Vast.ai
- ✅ **Base de données** : Supabase (gratuit jusqu'à 500MB)
- ✅ **Stockage** : Wasabi S3 (6€/mois pour 1TB)

**Ton site sera opérationnel en 1-2 heures !** 🏐