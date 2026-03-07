# 🚀 Commandes Simples pour Ubuntu

## 📝 **Problème :** Erreur 404 avec le téléchargement
Le fichier n'est pas encore disponible sur GitHub. Utilise ces commandes à la place.

---

## 🔧 **OPTION 1 : Télécharger depuis ICI (copie locale)**

### Sur ton PC Windows (maintenant) :
1. Ouvre l'explorateur de fichiers
2. Va dans : `Documents/CourtVision/courtvisionpro-main/courtvisionpro-main/purevolley-worker/`
3. Copie le fichier `tout-faire.sh` sur une clé USB

### Sur ton PC Ubuntu :
1. Branche la clé USB
2. Copie le fichier dans `~/Documents/`
3. Ouvre le terminal et fais :
   ```bash
   cd ~/Documents
   chmod +x tout-faire.sh
   ./tout-faire.sh
   ```

---

## 🔧 **OPTION 2 : Créer le fichier manuellement sur Ubuntu**

### Sur ton PC Ubuntu :
1. Ouvre le terminal
2. Tape :
   ```bash
   cd ~/Documents
   nano install-purevolley.sh
   ```
3. Copie-colle ce contenu :
   ```bash
   #!/bin/bash
   echo "🔧 Installation de Docker..."
   sudo apt update
   sudo apt install docker.io -y
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   
   echo "📥 Téléchargement du code..."
   git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
   cd volleyball-analyzer/purevolley-worker
   
   echo "⚙️  Configuration..."
   cp .env.example .env
   echo "⚠️  Ouvre un NOUVEAU terminal et fais : nano .env"
   echo "⚠️  Remplis avec tes infos Supabase et Wasabi"
   read -p "Quand c'est fait, appuie sur Entrée..." -n 1 -r
   
   echo "🔨 Construction Docker..."
   sudo docker build -t purevolley-worker .
   
   echo "🚀 Démarrage..."
   sudo docker run -d --name purevolley-worker --restart unless-stopped purevolley-worker
   
   echo "✅ Terminé ! Voir logs : sudo docker logs purevolley-worker"
   ```
4. Ctrl+X, puis Y, puis Entrée
5. Tape :
   ```bash
   chmod +x install-purevolley.sh
   ./install-purevolley.sh
   ```

---

## 🔧 **OPTION 3 : Commandes une par une (plus simple)**

### Étape 1 : Installer Docker
```bash
sudo apt update
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Étape 2 : Télécharger le code
```bash
cd ~/Documents
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer
cd volleyball-analyzer/purevolley-worker
```

### Étape 3 : Configurer
```bash
cp .env.example .env
nano .env  # Remplis avec tes infos
```

### Étape 4 : Construire Docker
```bash
sudo docker build -t purevolley-worker .
```

### Étape 5 : Démarrer
```bash
sudo docker run -d --name purevolley-worker --restart unless-stopped purevolley-worker
```

### Étape 6 : Vérifier
```bash
sudo docker logs purevolley-worker
```

---

## 🆘 **Si erreur GPU :**
```bash
# Arrêter le container
sudo docker stop purevolley-worker
sudo docker rm purevolley-worker

# Redémarrer avec GPU
sudo docker run -d \
  --name purevolley-worker \
  --restart unless-stopped \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --group-add render \
  --env HSA_OVERRIDE_GFX_VERSION=10.3.0 \
  purevolley-worker
```

---

## 📞 **Aide :**
Si bloqué :
1. **Copie l'erreur** exacte
2. **Dis-moi** quelle commande tu as tapée
3. **Prends une photo** de l'écran si possible

**Commence par l'OPTION 3 (commandes une par une) c'est plus simple !**