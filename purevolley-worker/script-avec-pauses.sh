#!/bin/bash
# 🚀 SCRIPT AVEC PAUSES - PUREVOLLEY WORKER
# Ce script s'arrête à chaque étape et attend que tu appuies sur Entrée.

echo "========================================="
echo "🚀 INSTALLATION PUREVOLLEY - AVEC PAUSES"
echo "========================================="
echo "Ce script va t'installer ton worker IA."
echo "Il s'arrêtera à chaque étape pour que tu"
echo "puisses vérifier et continuer à ton rythme."
echo ""
echo "⏱️  Temps total : 20-30 minutes"
echo "========================================="

pause() {
    echo ""
    echo "⏸️  PAUSE : Appuie sur Entrée pour continuer..."
    read -n 1 -r
    echo ""
}

# =========================================
# ÉTAPE 1 : Vérification système
# =========================================
echo ""
echo "🔍 ÉTAPE 1/10 : Vérification du système..."
echo "Vérifie que tu es sur Ubuntu 22.04."
echo "Si tu es sur Windows, arrête le script (Ctrl+C)."
pause

# =========================================
# ÉTAPE 2 : Mise à jour système
# =========================================
echo ""
echo "🔄 ÉTAPE 2/10 : Mise à jour du système..."
echo "Cette commande met à jour la liste des logiciels."
echo "Tape ton mot de passe si demandé."
echo ""
echo "Commande : sudo apt update"
pause

sudo apt update

echo ""
echo "✅ Mise à jour terminée."
pause

# =========================================
# ÉTAPE 3 : Installation Docker
# =========================================
echo ""
echo "🐳 ÉTAPE 3/10 : Installation de Docker..."
echo "Docker est comme une boîte pour ton programme."
echo "Cette installation prend 2-3 minutes."
echo ""
echo "Commande : sudo apt install docker.io -y"
pause

sudo apt install docker.io -y

echo ""
echo "✅ Docker installé."
pause

# =========================================
# ÉTAPE 4 : Démarrer Docker
# =========================================
echo ""
echo "⚡ ÉTAPE 4/10 : Démarrage de Docker..."
echo "On démarre le service Docker."
echo ""
echo "Commande : sudo systemctl start docker"
pause

sudo systemctl start docker
sudo systemctl enable docker

echo ""
echo "✅ Docker démarré."
pause

# =========================================
# ÉTAPE 5 : Ajouter ton utilisateur à Docker
# =========================================
echo ""
echo "👤 ÉTAPE 5/10 : Ajout à Docker..."
echo "Pour éviter de taper 'sudo' à chaque fois."
echo ""
echo "Commande : sudo usermod -aG docker \$USER"
pause

sudo usermod -aG docker $USER

echo ""
echo "✅ Utilisateur ajouté."
echo "⚠️  Redémarre l'ordinateur après le script pour que ça prenne effet."
pause

# =========================================
# ÉTAPE 6 : Télécharger le code
# =========================================
echo ""
echo "📥 ÉTAPE 6/10 : Téléchargement du code..."
echo "On télécharge ton programme depuis GitHub."
echo "Cette étape prend 1-2 minutes."
echo ""
echo "Commande : git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer"
pause

cd ~/Documents
git clone https://github.com/eduisjokxioejsdk-sudo/volleyball-analyzer

echo ""
echo "✅ Code téléchargé."
pause

# =========================================
# ÉTAPE 7 : Aller dans le bon dossier
# =========================================
echo ""
echo "📁 ÉTAPE 7/10 : Changement de dossier..."
echo "On va dans le dossier du worker."
echo ""
echo "Commande : cd volleyball-analyzer/purevolley-worker"
pause

cd volleyball-analyzer/purevolley-worker

echo ""
echo "✅ Dossier : $(pwd)"
pause

# =========================================
# ÉTAPE 8 : Configuration (.env)
# =========================================
echo ""
echo "⚙️  ÉTAPE 8/10 : Configuration..."
echo "On crée le fichier de configuration."
echo ""
echo "Commande : cp .env.example .env"
pause

cp .env.example .env

echo ""
echo "========================================="
echo "🔐 CONFIGURATION DES MOTS DE PASSE"
echo "========================================="
echo "⚠️  IMPORTANT : Ouvre un NOUVEAU terminal !"
echo ""
echo "Dans le NOUVEAU terminal, fais :"
echo "1. cd ~/Documents/volleyball-analyzer/purevolley-worker"
echo "2. nano .env"
echo "3. Remplis avec tes informations :"
echo "   - SUPABASE_URL (sur supabase.com → Settings → API)"
echo "   - SUPABASE_SERVICE_ROLE_KEY (même page)"
echo "   - WASABI_ACCESS_KEY (sur wasabi.com → Access Keys)"
echo "   - WASABI_SECRET_KEY (même page)"
echo "4. Ctrl+X, puis Y, puis Entrée"
echo ""
echo "⚠️  AJOUTE OBLIGATOIREMENT cette ligne :"
echo "HSA_OVERRIDE_GFX_VERSION=10.3.0"
echo ""
echo "Quand tu as fini, reviens ici et appuie sur Entrée."
pause

# Vérifier que le fichier .env n'est pas vide
if [ ! -s .env ] || grep -q "SUPABASE_URL=ton-url-ici" .env; then
    echo ""
    echo "❌ ATTENTION : Le fichier .env n'est pas rempli !"
    echo "Ouvre un terminal et fais : nano .env"
    echo "Remplis-le avant de continuer."
    echo ""
    echo "Appuie sur Entrée quand c'est fait..."
    pause
fi

# =========================================
# ÉTAPE 9 : Construction Docker
# =========================================
echo ""
echo "🔨 ÉTAPE 9/10 : Construction Docker..."
echo "Cette étape construit ton programme."
echo "⚠️  Ça prend 10-15 minutes !"
echo "Tu peux aller prendre un café ☕"
echo ""
echo "Commande : sudo docker build -t purevolley-worker ."
pause

sudo docker build -t purevolley-worker .

echo ""
echo "✅ Construction terminée."
pause

# =========================================
# ÉTAPE 10 : Démarrer le worker
# =========================================
echo ""
echo "🚀 ÉTAPE 10/10 : Démarrage du worker..."
echo "On démarre ton programme avec la carte graphique."
echo ""
echo "Commande longue (avec GPU) :"
echo "sudo docker run -d --name purevolley-worker ..."
pause

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

echo ""
echo "✅ Worker démarré !"
pause

# =========================================
# VÉRIFICATIONS FINALES
# =========================================
echo ""
echo "✅ INSTALLATION TERMINÉE !"
echo "========================================="
echo ""
echo "📊 Vérifications :"
echo ""
echo "1. Statut du worker :"
sudo docker ps | grep purevolley-worker || echo "❌ Worker non démarré"
echo ""
echo "2. Logs (dernières lignes) :"
sudo docker logs --tail 10 purevolley-worker 2>/dev/null || echo "❌ Pas de logs"
echo ""
echo "3. Test GPU :"
sudo docker exec purevolley-worker python check_gpu.py 2>/dev/null || echo "❌ Test GPU échoué"
echo ""
echo "========================================="
echo "🎉 FÉLICITATIONS !"
echo "========================================="
echo ""
echo "✅ CE QUI A ÉTÉ FAIT :"
echo "1. Docker installé"
echo "2. Code téléchargé"
echo "3. Programme construit"
echo "4. Worker démarré avec GPU"
echo ""
echo "📋 PROCHAINES ÉTAPES :"
echo "1. Redémarre ton ordinateur"
echo "2. Vérifie les logs : sudo docker logs purevolley-worker"
echo "3. Teste avec une vidéo sur ton site"
echo ""
echo "🆘 EN CAS DE PROBLÈME :"
echo "1. Logs : sudo docker logs purevolley-worker"
echo "2. Redémarre : sudo docker restart purevolley-worker"
echo "3. Demande-moi de l'aide avec le message d'erreur"
echo ""
echo "💡 ASTUCE :"
echo "Le worker surveille automatiquement les nouvelles vidéos."
echo "Quand tu uploades une vidéo sur ton site, il la traite !"
echo ""
echo "========================================="
echo "Bonne chance avec ton analyseur de volley ! 🏐"
echo "========================================="

# Demander redémarrage
echo ""
echo "🔄 REDÉMARRAGE RECOMMANDÉ"
echo "Pour que les groupes (docker, video) soient activés,"
echo "redémarre ton ordinateur maintenant."
echo ""
read -p "Redémarrer maintenant ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "Redémarrage dans 5 secondes..."
    sleep 5
    sudo reboot
else
    echo "Redémarre manuellement plus tard."
fi