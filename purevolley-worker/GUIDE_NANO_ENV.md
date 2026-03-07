# 📝 GUIDE COMPLET : REMPLIR LE FICHIER .env AVEC NANO

## 🎯 **Objectif :**
Remplir le fichier `.env` avec tes informations Supabase et Wasabi.

---

## 📋 **ÉTAPE 1 : OUVERTURE DU FICHIER**

### Sur Ubuntu, dans le terminal :
```bash
# 1. Va dans le bon dossier
cd ~/Documents/purevolley-worker

# 2. Ouvre le fichier avec nano
nano .env
```

**Tu verras ceci :**
```
SUPABASE_URL=ton-url-ici
SUPABASE_SERVICE_ROLE_KEY=ta-cle-secrete-ici
WASABI_ACCESS_KEY=ta-cle-wasabi-ici
WASABI_SECRET_KEY=ton-secret-wasabi-ici
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
HSA_OVERRIDE_GFX_VERSION=10.3.0
```

---

## 📋 **ÉTAPE 2 : TROUVER LES INFORMATIONS SUPABASE**

### 1. **Ouvre ton navigateur web** (sur Windows ou Ubuntu)
- Va sur [supabase.com](https://supabase.com)
- Connecte-toi avec ton compte

### 2. **Va dans ton projet PureVolley**
- Clique sur ton projet

### 3. **Trouve l'URL :**
- Va dans **Settings** (roue dentée en bas à gauche)
- Clique sur **API**
- Cherche **"Project URL"**
- **Copie** l'URL (ex: `https://abc123.supabase.co`)

### 4. **Trouve la clé secrète :**
- Toujours dans **Settings → API**
- Descends jusqu'à **"Project API keys"**
- Cherche **"service_role secret"**
- **Copie** la clé (commence par `sb.`)

---

## 📋 **ÉTAPE 3 : TROUVER LES INFORMATIONS WASABI**

### 1. **Ouvre Wasabi dans ton navigateur**
- Va sur [wasabi.com](https://wasabi.com)
- Connecte-toi avec ton compte

### 2. **Trouve les clés d'accès :**
- Clique sur ton nom en haut à droite
- Va dans **"Access Keys"**
- Si tu n'as pas de clé, clique sur **"Create New Access Key"**
- **Copie** :
  - **Access Key** (ex: `ABCDEFGHIJKLMNOPQRST`)
  - **Secret Key** (ex: `abcdefghijklmnopqrstuvwxyz0123456789ABCD`)

---

## 📋 **ÉTAPE 4 : REMPLIR LE FICHIER .env AVEC NANO**

### **Dans nano, tu vois :**
```
SUPABASE_URL=ton-url-ici
SUPABASE_SERVICE_ROLE_KEY=ta-cle-secrete-ici
WASABI_ACCESS_KEY=ta-cle-wasabi-ici
WASABI_SECRET_KEY=ton-secret-wasabi-ici
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
HSA_OVERRIDE_GFX_VERSION=10.3.0
```

### **Comment éditer :**
1. **Utilise les flèches** du clavier pour te déplacer
2. **Efface** `ton-url-ici` et **colle** ton URL Supabase
3. **Efface** `ta-cle-secrete-ici` et **colle** ta clé service_role
4. **Efface** `ta-cle-wasabi-ici` et **colle** ton Access Key Wasabi
5. **Efface** `ton-secret-wasabi-ici` et **colle** ton Secret Key Wasabi

### **Exemple terminé :**
```
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb.abc123def456ghi789jkl012mno345pqr678stu901
WASABI_ACCESS_KEY=ABCDEFGHIJKLMNOPQRST
WASABI_SECRET_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCD
WASABI_BUCKET=purevolley
WASABI_REGION=us-east-1
WASABI_ENDPOINT=https://s3.wasabisys.com
HSA_OVERRIDE_GFX_VERSION=10.3.0
```

---

## 📋 **ÉTAPE 5 : SAUVEGARDER ET QUITTER NANO**

### **Une fois que tout est rempli :**
1. **Appuie sur `Ctrl+X`** (pour quitter)
2. **Appuie sur `Y`** (pour sauvegarder)
3. **Appuie sur `Entrée`** (pour confirmer le nom du fichier)

**✅ Le fichier est maintenant sauvegardé !**

---

## 📋 **ÉTAPE 6 : VÉRIFICATION**

### Pour vérifier que le fichier est bien rempli :
```bash
# Affiche le contenu du fichier
cat .env

# Vérifie qu'il n'y a plus "ton-url-ici"
grep -v "ton-url-ici" .env
```

**Tu devrais voir tes vraies informations, pas les exemples.**

---

## 🆘 **PROBLÈMES COURANTS**

### **Problème : Je ne trouve pas les clés Supabase**
- Vérifie que tu es dans le **bon projet** Supabase
- Vérifie que tu es dans **Settings → API**
- La clé `service_role` est en bas de page

### **Problème : Je ne trouve pas les clés Wasabi**
- Vérifie que tu es connecté au bon compte Wasabi
- Les clés sont dans **"Access Keys"**
- Crée une nouvelle clé si nécessaire

### **Problème : Nano ne fonctionne pas**
```bash
# Si nano n'est pas installé :
sudo apt install nano

# Ou utilise un autre éditeur :
gedit .env  # (interface graphique)
vim .env    # (plus complexe)
```

### **Problème : J'ai fait une erreur**
```bash
# Réouvre le fichier :
nano .env

# Corrige l'erreur
# Ctrl+X, Y, Entrée
```

---

## 💡 **CONSEILS IMPORTANTS**

### **1. Ne partage jamais ton fichier .env !**
Il contient tes mots de passe. Ne l'envoie à personne.

### **2. Vérifie chaque ligne**
- Pas d'espaces avant ou après le `=`
- Pas de guillemets autour des valeurs
- Chaque valeur sur sa propre ligne

### **3. La ligne GPU est OBLIGATOIRE**
```
HSA_OVERRIDE_GFX_VERSION=10.3.0
```
**Ne l'efface pas !** Elle est nécessaire pour ta carte graphique AMD RX 6600.

### **4. Si tu changes d'ordinateur**
Tu devras recréer le fichier `.env` avec les nouvelles informations.

---

## 📞 **AIDE**

### **Si tu es bloqué :**
1. **Prends une photo** de ton écran nano
2. **Prends une photo** de tes pages Supabase/Wasabi (cache les mots de passe)
3. **Envoie-moi** les photos et je te guide

### **Alternative : Éditeur graphique**
Si nano est trop difficile :
```bash
# Sur Ubuntu avec interface graphique :
gedit .env

# Ça ouvre une fenêtre comme le Bloc-notes
# Édite, sauvegarde, ferme
```

---

## 🎉 **FÉLICITATIONS !**

**Une fois le fichier `.env` rempli :**
1. ✅ Retourne dans le terminal où tourne le script
2. ✅ Appuie sur **Entrée** pour continuer
3. ✅ Le script construira Docker et démarrera ton worker

**Ton analyseur de vidéos de volley sera bientôt opérationnel !** 🏐