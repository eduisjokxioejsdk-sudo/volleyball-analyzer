# 🚀 Étapes Finales - Migration Railway → PC Ubuntu

## 📋 État Actuel
- ✅ ROCm 6.1 installé sur PC Ubuntu avec RX 6600
- ✅ Code PureVolley Worker créé et poussé sur GitHub
- ✅ Configuration Coolify pré-préparée
- ❌ Worker non déployé sur Coolify
- ❌ Intégration site ↔ worker non testée

---

## 🎯 Objectif Final
Votre site web (Vercel) envoie des vidéos → Votre PC Ubuntu (Coolify) les analyse → Résultats retournés au site

---

## 📝 Liste Étape par Étape

### **ÉTAPE 1 : Vérification GPU sur votre PC Ubuntu**
```bash
# Sur votre PC Ubuntu :
cd ~
python3 -c "import torch; print(f'GPU: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# Si pas de PyTorch :
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
```

**Résultat attendu :** `GPU: True` et `Device: AMD Radeon RX 6600`

### **ÉTAPE 2 : Préparation des variables d'environnement**
```bash
cd purevolley-worker
cp .env.example .env
# Éditer .env avec vos vraies valeurs :
nano .env
```

**Variables CRITIQUES à remplir :**
```
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_SERVICE_ROLE_KEY=votre-cle-secrete
WASABI_ACCESS_KEY=votre-cle-wasabi
WASABI_SECRET_KEY=votre-secret-wasabi
HSA_OVERRIDE_GFX_VERSION=10.3.0
```

### **ÉTAPE 3 : Test local du worker (sans Coolify)**
```bash
cd purevolley-worker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test GPU :
python check_gpu.py

# Test connexions :
python -c "
from supabase import create_client
import boto3
print('✅ Bibliothèques importées')
"

# Test complet (optionnel) :
python worker.py --test
```

### **ÉTAPE 4 : Déploiement sur Coolify**

#### 4.1. Préparation des fichiers Coolify
```bash
cd purevolley-worker
bash setup-coolify.sh
# Génère le dossier coolify-deploy/
```

#### 4.2. Configuration dans Coolify (votre-IP:8000)
1. **Nouvelle Application** → GitHub → votre repository
2. **Build Settings** :
   - Build Type: `Dockerfile`
   - Dockerfile Path: `purevolley-worker/Dockerfile`
   - Build Context: `purevolley-worker`
3. **Environment Variables** :
   - Copier-coller depuis votre fichier `.env`
4. **Docker Settings** (CRITIQUE) :
   ```yaml
   devices:
     - /dev/kfd
     - /dev/dri
   group_add:
     - video
     - render
   ```
5. **Déployer** et surveiller les logs

### **ÉTAPE 5 : Vérification du déploiement Coolify**

Dans les logs Coolify, cherchez :
```
✅ GPU disponible: AMD Radeon RX 6600
✅ Connexion à Supabase établie
✅ Connexion à Wasabi S3 établie
🚀 Démarrage du PureVolley Worker
```

### **ÉTAPE 6 : Configuration de la base de données Supabase**

#### 6.1. Vérifier/Créer la table `matches`
```sql
-- Dans l'éditeur SQL de Supabase :
CREATE TABLE IF NOT EXISTS matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_url TEXT NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activer RLS (Row Level Security)
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;

-- Politique pour le service role (worker)
CREATE POLICY "Service role full access" ON matches
  FOR ALL USING (auth.role() = 'service_role');
```

#### 6.2. Tester l'insertion manuelle
```sql
INSERT INTO matches (video_url, status) 
VALUES ('s3://purevolley/test-video.mp4', 'pending');
```

### **ÉTAPE 7 : Intégration avec votre site web (Frontend)**

#### 7.1. Vérifier le flux actuel de votre site
Regardez dans votre code frontend (`src/lib/volleyVisionApi.ts` ou similaire) :
- Où sont uploadées les vidéos ?
- Comment sont-elles envoyées à l'API ?
- Comment les résultats sont-ils récupérés ?

#### 7.2. Adapter pour utiliser le nouveau worker
Le worker surveille la table `matches` avec `status='pending'`.
Votre site doit :
1. Uploader la vidéo sur Wasabi S3
2. Insérer une ligne dans `matches` avec `video_url` et `status='pending'`
3. Le worker détectera automatiquement et traitera
4. Votre site peut surveiller le `status` (polling ou WebSockets)

### **ÉTAPE 8 : Test du flux complet**

#### Test manuel :
1. **Upload vidéo** via votre site
2. **Vérifier Supabase** : Nouvelle ligne dans `matches` avec `status='pending'`
3. **Vérifier Coolify logs** : Worker détecte et traite
4. **Vérifier Supabase** : `status` passe à `'processing'` puis `'completed'`
5. **Vérifier Wasabi** : Logs uploadés dans le bucket
6. **Vérifier votre site** : Résultats affichés

### **ÉTAPE 9 : Monitoring et optimisation**

#### 9.1. Monitoring de base :
```bash
# Sur votre PC Ubuntu :
docker stats  # Si utilisé via Docker
htop          # Utilisation CPU/GPU
rocm-smi      # Statut GPU AMD
```

#### 9.2. Logs :
- **Coolify** : Logs d'application
- **Supabase** : Logs de la table `matches`
- **Wasabi** : Logs d'accès S3

#### 9.3. Alertes :
Configurer des alertes pour :
- GPU non disponible
- Échecs de traitement
- Temps de traitement anormalement long

### **ÉTAPE 10 : Passage en production**

#### 10.1. Tests de charge :
- Tester avec plusieurs vidéos simultanées
- Surveiller l'utilisation GPU/RAM

#### 10.2. Backup/restauration :
- Sauvegarder la configuration Coolify
- Documenter les étapes de déploiement

#### 10.3. Documentation :
- Documenter le flux pour votre équipe
- Créer un runbook de dépannage

---

## ⚠️ Points de Vérification Critiques

### **1. GPU Detection**
```
✅ rocminfo fonctionne
✅ torch.cuda.is_available() = True
✅ HSA_OVERRIDE_GFX_VERSION=10.3.0
```

### **2. Connexions Réseau**
```
✅ PC Ubuntu → Internet
✅ PC Ubuntu → Supabase
✅ PC Ubuntu → Wasabi S3
✅ Coolify → Devices GPU
```

### **3. Permissions**
```
✅ Service role Supabase a accès à la table matches
✅ Clés Wasabi ont accès au bucket
✅ User Docker a accès à /dev/kfd et /dev/dri
```

### **4. Flux de données**
```
✅ Site → Wasabi (upload vidéo)
✅ Site → Supabase (création match)
✅ Worker → Supabase (lecture matches)
✅ Worker → Wasabi (téléchargement vidéo)
✅ Worker → GPU (traitement)
✅ Worker → Supabase (mise à jour status)
✅ Worker → Wasabi (upload logs)
✅ Site → Supabase (lecture résultats)
```

---

## 🔧 Dépannage Rapide

### **Problème : GPU non détecté dans Coolify**
```bash
# Sur votre PC Ubuntu :
ls -la /dev/kfd
ls -la /dev/dri
groups
# Vérifier que l'utilisateur Docker est dans les groupes video et render
```

### **Problème : Connexion Supabase échoue**
- Vérifier `SUPABASE_SERVICE_ROLE_KEY`
- Vérifier les permissions RLS
- Tester avec `curl` depuis le PC Ubuntu

### **Problème : Connexion Wasabi échoue**
- Vérifier les clés d'accès
- Tester avec `aws s3 ls` (avec endpoint Wasabi)
- Vérifier les permissions du bucket

### **Problème : Worker ne détecte pas les nouveaux matches**
- Vérifier que `status='pending'`
- Vérifier le `poll_interval` dans le worker
- Vérifier les logs Coolify pour erreurs

---

## 🎉 Validation Finale

Votre système est opérationnel quand :

1. **Upload vidéo sur site** → Vidéo sur Wasabi
2. **Création match sur site** → Ligne dans Supabase
3. **Worker Coolify** → Détecte et traite en < 1 minute
4. **Status match** → Passe de 'pending' à 'completed'
5. **Résultats** → Disponibles sur votre site

**Temps estimé pour compléter toutes les étapes : 2-4 heures**

---

## 📞 Support

Si bloqué à une étape :
1. Consulter les logs Coolify
2. Vérifier les permissions
3. Tester chaque composant isolément
4. Documenter l'erreur exacte

**Rappel :** Vous remplacez Railway (cloud) par votre PC Ubuntu (local) avec GPU dédié. Les économies et performances justifient l'investissement en temps !