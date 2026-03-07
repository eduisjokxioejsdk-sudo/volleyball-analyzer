# 📁 INSTRUCTIONS POUR CLÉ USB

## 🎯 **Objectif :**
Copier tous les fichiers sur une clé USB, puis les transférer sur ton PC Ubuntu.

---

## 📋 **ÉTAPE 1 : Préparer la clé USB sur Windows**

### 1. **Insère ta clé USB** dans ton PC Windows
- Attends qu'elle soit détectée
- Note la lettre du lecteur (ex: `E:`)

### 2. **Crée un dossier** sur la clé USB
- Ouvre l'explorateur de fichiers
- Va dans ta clé USB
- Crée un dossier : `PureVolley-Installation`

### 3. **Copie ces fichiers** depuis ton PC Windows :
Va dans : `Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/purevolley-worker/`

**Fichiers à copier :**
```
📄 script-avec-pauses.sh      (Script principal avec pauses)
📄 COMMANDES_SIMPLES.md       (Commandes étape par étape)
📄 GUIDE_DEBUTANT.md          (Guide 13 étapes)
📄 ETAPES_FINALES.md          (Liste détaillée)
📄 tout-faire.sh              (Script automatique)
📄 check_gpu.py               (Test carte graphique)
📄 .env.example               (Modèle de configuration)
📄 README.md                  (Instructions générales)
📄 requirements.txt           (Dépendances Python)
📄 Dockerfile                 (Configuration Docker)
📄 worker.py                  (Programme principal)
```

### 4. **Vérifie que tu as tous les fichiers :**
Dans le dossier `PureVolley-Installation` sur ta clé USB, tu dois avoir **au moins 12 fichiers**.

---

## 📋 **ÉTAPE 2 : Transférer sur Ubuntu**

### 1. **Débranche la clé USB** de Windows
- Clique sur "Éjecter" dans la barre des tâches
- Attends le message "Périphérique peut être retiré"

### 2. **Branche la clé USB** sur ton PC Ubuntu
- Attends qu'elle soit détectée
- Elle devrait s'ouvrir automatiquement

### 3. **Copier les fichiers** sur Ubuntu :
```bash
# Ouvre le terminal sur Ubuntu
# Copie le dossier entier
cp -r /media/$USER/NOM_DE_TA_CLÉ/PureVolley-Installation ~/Documents/

# Va dans le dossier
cd ~/Documents/PureVolley-Installation
```

**Si la clé USB ne s'ouvre pas automatiquement :**
```bash
# Vérifie où est la clé USB
lsblk

# Monte la clé USB (remplace sdb1 par ton lecteur)
sudo mount /dev/sdb1 /mnt

# Copie les fichiers
cp -r /mnt/PureVolley-Installation ~/Documents/
```

---

## 📋 **ÉTAPE 3 : Installer sur Ubuntu**

### **OPTION A : Avec le script principal (recommandé)**
```bash
# 1. Va dans le dossier
cd ~/Documents/PureVolley-Installation

# 2. Rend le script exécutable
chmod +x script-avec-pauses.sh

# 3. Exécute le script
./script-avec-pauses.sh
```

### **OPTION B : Commandes manuelles**
Suis les instructions dans `COMMANDES_SIMPLES.md`

### **OPTION C : Script automatique**
```bash
cd ~/Documents/PureVolley-Installation
chmod +x tout-faire.sh
./tout-faire.sh
```

---

## 🆘 **DÉPANNAGE CLÉ USB**

### **Problème : Clé USB non détectée sur Ubuntu**
```bash
# Vérifie les périphériques USB
lsusb

# Vérifie les disques
lsblk

# Formate en FAT32 (ATTENTION : efface tout !)
sudo mkfs.vfat -F 32 /dev/sdb1
```

### **Problème : Permissions refusées**
```bash
# Donne les permissions
chmod +x *.sh
chmod +x *.py
```

### **Problème : Fichiers manquants**
Vérifie que tu as copié tous les fichiers depuis Windows.

---

## 📁 **STRUCTURE DES FICHIERS SUR LA CLÉ USB**

```
PureVolley-Installation/
├── 🚀 script-avec-pauses.sh      (EXÉCUTE CELUI-CI !)
├── 📝 COMMANDES_SIMPLES.md       (Instructions texte)
├── 🎓 GUIDE_DEBUTANT.md          (Guide débutant)
├── 📋 ETAPES_FINALES.md          (Liste complète)
├── ⚡ tout-faire.sh              (Script automatique)
├── 🎮 check_gpu.py               (Test GPU)
├── 🔐 .env.example               (Modèle configuration)
├── 📖 README.md                  (Instructions)
├── 📦 requirements.txt           (Dépendances)
├── 🐳 Dockerfile                 (Docker)
└── 🤖 worker.py                  (Programme)
```

---

## 💡 **CONSEILS IMPORTANTS**

### **1. Lis les instructions à l'écran**
Le script `script-avec-pauses.sh` s'arrête à chaque étape. **Lis ce qui s'affiche !**

### **2. Configure ton fichier `.env`**
Le script te guidera pour :
- Ouvrir un **nouveau terminal**
- Éditer le fichier `.env`
- Remplir avec tes infos Supabase/Wasabi

### **3. Sois patient**
- Installation Docker : 2-3 minutes
- Construction Docker : 10-15 minutes
- Total : 20-30 minutes

### **4. Redémarre après installation**
Pour que les groupes (docker, video) soient activés.

---

## 📞 **AIDE**

### **Si bloqué pendant l'installation :**
1. **Prends une photo** de l'écran avec ton téléphone
2. **Copie le message d'erreur** exact
3. **Dis-moi** à quelle étape tu es

### **Fichiers de secours :**
- `COMMANDES_SIMPLES.md` : Commandes une par une
- `GUIDE_DEBUTANT.md` : Guide détaillé

---

## 🎉 **BONNE INSTALLATION !**

**Résumé des étapes :**
1. ✅ **Windows** : Copie les fichiers sur clé USB
2. ✅ **Ubuntu** : Transfère les fichiers depuis la clé USB
3. ✅ **Ubuntu** : Exécute `./script-avec-pauses.sh`
4. ✅ **Ubuntu** : Suis les instructions à l'écran
5. ✅ **Ubuntu** : Redémarre l'ordinateur
6. ✅ **Test** : Vérifie avec `sudo docker logs purevolley-worker`

**Tu es prêt à analyser tes vidéos de volley !** 🏐