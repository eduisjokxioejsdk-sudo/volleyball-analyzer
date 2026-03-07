# 🎓 Guide Débutant - PureVolley Worker

## 👋 Bonjour ! Je vais te guider pas à pas

Ne t'inquiète pas si tu es débutant. Je vais tout t'expliquer comme si c'était la première fois. On va y aller **très lentement**, une étape à la fois.

---

## 📍 **ÉTAPE 0 : Où es-tu ?**

**Réponds à cette question :**
- [ ] **Je suis sur mon PC Windows** (celui où tu lis ce message)
- [ ] **Je suis sur mon PC Ubuntu** (celui avec la carte graphique AMD)

**Si tu es sur Windows :**
- On va préparer les fichiers ici
- Puis tu iras sur ton PC Ubuntu pour les étapes suivantes

**Si tu es sur Ubuntu :**
- Parfait ! On commence directement

---

## 📁 **ÉTAPE 1 : Ouvrir le bon dossier**

### Sur Windows (maintenant) :
1. Ouvre l'explorateur de fichiers
2. Va dans : `Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/`
3. Trouve le dossier `purevolley-worker`
4. Ouvre-le (double-clic)

### Sur Ubuntu (plus tard) :
1. Ouvre le terminal (Ctrl+Alt+T)
2. Tape : `cd ~/Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/purevolley-worker`
3. Appuie sur Entrée

**✅ Objectif :** Être dans le dossier `purevolley-worker`

---

## 🔧 **ÉTAPE 2 : Créer le fichier de configuration**

### C'est quoi un fichier `.env` ?
C'est un fichier texte simple qui contient tes mots de passe et adresses. Comme un carnet d'adresses pour ton programme.

### Comment faire :
1. Dans le dossier `purevolley-worker`, cherche le fichier `.env.example`
2. Fais un clic droit → "Copier"
3. Fais un clic droit → "Coller"
4. Renomme la copie en `.env` (supprime le `.example`)

**Tu dois avoir deux fichiers :**
- `.env.example` (le modèle)
- `.env` (ta copie personnelle)

---

## ✏️ **ÉTAPE 3 : Remplir le fichier .env**

Ouvre le fichier `.env` avec le Bloc-notes (Windows) ou `nano` (Ubuntu).

### Les informations à trouver :

#### 1. **Supabase** (ta base de données en ligne)
- Va sur [supabase.com](https://supabase.com)
- Connecte-toi à ton projet
- Va dans "Settings" → "API"
- Copie :
  - `URL` → Mets-le dans `SUPABASE_URL=`
  - `service_role secret` → Mets-le dans `SUPABASE_SERVICE_ROLE_KEY=`

#### 2. **Wasabi** (ton stockage de vidéos)
- Va sur [wasabi.com](https://wasabi.com)
- Connecte-toi
- Va dans "Access Keys"
- Crée une nouvelle clé si besoin
- Copie :
  - `Access Key` → `WASABI_ACCESS_KEY=`
  - `Secret Key` → `WASABI_SECRET_KEY=`

#### 3. **GPU** (ta carte graphique)
- Pour l'AMD RX 6600, ajoute toujours :
  ```
  HSA_OVERRIDE_GFX_VERSION=10.3.0
  ```

### 📝 **Exemple de fichier .env terminé :**
```
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb.abc123...xyz
WASABI_ACCESS_KEY=ABCDEFGHIJKLMNOPQRST
WASABI_SECRET_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCD
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
HSA_OVERRIDE_GFX_VERSION=10.3.0
```

**⚠️ Attention :** Ne partage jamais ce fichier ! Il contient tes mots de passe.

---

## 🖥️ **ÉTAPE 4 : Aller sur ton PC Ubuntu**

Maintenant, va sur ton PC Ubuntu (celui avec la carte graphique).

### Si tu as les fichiers sur Windows :
1. Copie le dossier `purevolley-worker` sur une clé USB
2. Branche la clé USB sur ton PC Ubuntu
3. Copie le dossier dans `Documents/`

### Si tu as GitHub :
1. Sur Ubuntu, ouvre le terminal
2. Tape : `git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer`
3. Tape : `cd volleyball-analyzer/purevolley-worker`

---

## 🧪 **ÉTAPE 5 : Tester la carte graphique**

### C'est quoi PyTorch ?
C'est un programme qui permet d'utiliser la carte graphique pour l'IA.

### Comment tester :
1. Ouvre le terminal sur Ubuntu
2. Tape : `cd ~/Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/purevolley-worker`
3. Tape : `python3 check_gpu.py`

### 📊 **Résultats possibles :**

#### ✅ **Si ça marche :**
```
✅ GPU disponible!
  Nom: AMD Radeon RX 6600
```

#### ❌ **Si ça ne marche pas :**
```
❌ Aucun GPU disponible
```

### 🔧 **Si ça ne marche pas :**
1. Vérifie que ROCm 6.1 est installé :
   ```bash
   rocminfo
   ```
2. Si erreur, installe ROCm :
   ```bash
   sudo apt update
   sudo apt install rocm-hip-sdk
   ```

---

## 🐳 **ÉTAPE 6 : Installer Docker (si pas déjà fait)**

### C'est quoi Docker ?
C'est comme une boîte qui contient tout ce dont ton programme a besoin.

### Comment installer :
1. Ouvre le terminal
2. Tape ces commandes une par une :

```bash
# 1. Mettre à jour
sudo apt update

# 2. Installer Docker
sudo apt install docker.io

# 3. Démarrer Docker
sudo systemctl start docker
sudo systemctl enable docker

# 4. Ajouter ton utilisateur à Docker (pour éviter "sudo")
sudo usermod -aG docker $USER

# 5. Redémarre l'ordinateur
sudo reboot
```

**💡 Astuce :** Après le redémarrage, rouvre le terminal.

---

## 🚀 **ÉTAPE 7 : Tester Docker avec ton programme**

1. Retourne dans le dossier :
   ```bash
   cd ~/Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/purevolley-worker
   ```

2. Construire l'image Docker (ça prend 5-10 minutes) :
   ```bash
   docker build -t purevolley-worker .
   ```

3. Tester l'image :
   ```bash
   docker run --rm purevolley-worker python check_gpu.py
   ```

### 📊 **Résultats :**
- Si tu vois `✅ GPU disponible!` → Parfait !
- Si erreur → On verra ensemble.

---

## 🌐 **ÉTAPE 8 : Installer Coolify**

### C'est quoi Coolify ?
C'est un programme qui gère tes applications (comme ton worker) automatiquement.

### Comment installer :
1. Ouvre le terminal
2. Tape :
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
   ```
3. Attends la fin de l'installation
4. Ouvre ton navigateur web
5. Va à l'adresse : `http://ton-ip-ubuntu:8000`
   - Remplace `ton-ip-ubuntu` par l'adresse IP de ton PC Ubuntu
   - Pour trouver l'IP : `ip addr show` dans le terminal

---

## 📦 **ÉTAPE 9 : Configurer Coolify**

### Première connexion :
1. Dans ton navigateur (sur Windows), va à : `http://192.168.1.X:8000`
   (remplace X par le dernier chiffre de l'IP de ton Ubuntu)
2. Crée un compte admin
3. Connecte-toi

### Ajouter ton projet :
1. Clique sur "Create New Resource"
2. Choisis "Application"
3. Choisis "GitHub"
4. Connecte ton compte GitHub
5. Sélectionne ton projet `volleyball-analyzer`

### Configuration IMPORTANTE :
1. **Build Type** : `Dockerfile`
2. **Dockerfile Path** : `purevolley-worker/Dockerfile`
3. **Build Context** : `purevolley-worker`

### Variables d'environnement :
1. Clique sur "Environment Variables"
2. Copie-colle tout le contenu de ton fichier `.env`
3. Clique sur "Save"

### Configuration GPU (CRITIQUE) :
1. Clique sur "Docker Settings"
2. Ajoute dans "Devices" :
   ```
   /dev/kfd
   /dev/dri
   ```
3. Ajoute dans "Group Add" :
   ```
   video
   render
   ```

---

## 🎬 **ÉTAPE 10 : Démarrer le worker**

1. Clique sur "Deploy"
2. Attends 5-10 minutes (première fois plus long)
3. Clique sur "Logs" pour voir ce qui se passe

### 👀 **Ce qu'il faut voir dans les logs :**
```
✅ GPU disponible: AMD Radeon RX 6600
✅ Connexion à Supabase établie
✅ Connexion à Wasabi S3 établie
🚀 Démarrage du PureVolley Worker
```

---

## 🧪 **ÉTAPE 11 : Tester avec une vraie vidéo**

### Préparer Supabase :
1. Va sur [supabase.com](https://supabase.com)
2. Va dans l'éditeur SQL
3. Copie-colle ce code :
   ```sql
   INSERT INTO matches (video_url, status) 
   VALUES ('s3://purevolley/test-video.mp4', 'pending');
   ```
4. Clique sur "Run"

### Vérifier Coolify :
1. Retourne dans Coolify
2. Regarde les logs
3. Tu devrais voir :
   ```
   📥 Nouveau match détecté: test-video.mp4
   ⚙️ Traitement en cours...
   ✅ Traitement terminé!
   ```

---

## 🌐 **ÉTAPE 12 : Connecter ton site web**

### Sur ton site (Vercel) :
1. Ouvre ton code sur GitHub
2. Cherche où les vidéos sont uploadées
3. Modifie pour :
   - Uploader sur Wasabi
   - Ajouter une ligne dans la table `matches` de Supabase

### Exemple simple :
```javascript
// Après avoir uploadé la vidéo sur Wasabi
await supabase.from('matches').insert({
  video_url: 's3://purevolley/ma-video.mp4',
  status: 'pending'
});
```

---

## 🔍 **ÉTAPE 13 : Vérifier que tout marche**

### Test complet :
1. **Sur ton site** : Upload une vidéo
2. **Sur Supabase** : Vérifie qu'une nouvelle ligne apparaît
3. **Sur Coolify** : Vérifie que le worker la traite
4. **Sur ton site** : Vérifie que les résultats s'affichent

### Temps attendu :
- Upload vidéo : 1-2 minutes
- Traitement worker : 5-10 minutes
- Affichage résultats : Immédiat après traitement

---

## 🆘 **PROBLÈMES COURANTS ET SOLUTIONS**

### ❌ "GPU non disponible"
```bash
# Sur Ubuntu :
sudo apt install rocm-hip-sdk
sudo reboot
```

### ❌ "Connexion Supabase échoue"
- Vérifie `SUPABASE_SERVICE_ROLE_KEY`
- Vérifie que la table `matches` existe

### ❌ "Connexion Wasabi échoue"
- Vérifie les clés d'accès
- Vérifie que le bucket `purevolley` existe

### ❌ "Coolify ne démarre pas"
```bash
# Redémarrer Coolify :
sudo systemctl restart coolify
```

---

## 🎉 **FÉLICITATIONS !**

Tu as maintenant :
- ✅ Un worker IA sur ton PC Ubuntu
- ✅ Qui utilise ta carte graphique AMD RX 6600
- ✅ Connecté à ton site web
- ✅ Qui analyse les vidéos automatiquement

**Prochaine étape :** M'envoyer un message avec où tu bloques, et on résout ensemble !

---

## 📞 **CONTACT**

Si tu es bloqué :
1. Prends une photo de l'erreur
2. Envoie-moi le message d'erreur exact
3. Dis-moi à quelle étape tu es

**Rappel :** On y va une étape à la fois. Pas de pression ! 😊