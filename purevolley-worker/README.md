# PureVolley Worker

Worker local pour le découpage de matchs de volley par IA, tournant sur PC Ubuntu avec carte graphique AMD RX 6600 (ROCm 6.1).

## 🎯 Fonctionnalités

- Surveillance automatique des matchs en attente dans Supabase
- Téléchargement des vidéos depuis Wasabi S3
- Vérification de la disponibilité GPU (AMD RX 6600 avec ROCm 6.1)
- Simulation de traitement IA (5 secondes) - prêt pour l'intégration VideoMAE
- Mise à jour des statuts dans Supabase
- Upload des logs de traitement sur Wasabi S3

## 🛠️ Stack Technique

- **OS Hôte**: Ubuntu 22.04
- **GPU**: AMD Radeon RX 6600 (ROCm 6.1, `HSA_OVERRIDE_GFX_VERSION=10.3.0`)
- **Backend**: Supabase (table `matches` avec colonnes `id`, `video_url`, `status`)
- **Stockage**: Wasabi S3 (Bucket `purevolley`)
- **Conteneurisation**: Docker avec GPU Passthrough

## 📁 Structure des Fichiers

```
purevolley-worker/
├── Dockerfile              # Image Docker basée sur rocm/dev-ubuntu-22.04:6.1
├── requirements.txt        # Dépendances Python avec ROCm 6.1
├── worker.py              # Script principal du worker
├── .env.example           # Template des variables d'environnement
└── README.md              # Ce fichier
```

## 🚀 Déploiement avec Coolify

### 1. Prérequis

- Serveur Ubuntu 22.04 avec AMD RX 6600
- ROCm 6.1 installé sur l'hôte
- Coolify installé et configuré
- Accès à Supabase et Wasabi S3

### 2. Configuration GPU Passthrough dans Coolify

Pour permettre l'accès au GPU depuis le conteneur Docker, ajoutez les devices et groupes suivants dans la configuration Docker de Coolify :

```yaml
# Dans la configuration Docker de votre application Coolify
devices:
  - /dev/kfd
  - /dev/dri

group_add:
  - video
  - render

environment:
  - HSA_OVERRIDE_GFX_VERSION=10.3.0
  - ROCM_PATH=/opt/rocm
```

### 3. Variables d'Environnement

Configurez les variables suivantes dans Coolify :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `SUPABASE_URL` | URL de votre projet Supabase | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé service role de Supabase | `eyJhbGciOiJIUzI1NiIs...` |
| `WASABI_ACCESS_KEY` | Clé d'accès Wasabi S3 | `ABCDEFGHIJKLMNOPQRST` |
| `WASABI_SECRET_KEY` | Clé secrète Wasabi S3 | `abcdefghijklmnopqrstuvwxyz0123456789ABCD` |
| `WASABI_BUCKET` | Nom du bucket Wasabi | `purevolley` |
| `WASABI_REGION` | Région Wasabi | `us-east-1` |
| `WASABI_ENDPOINT` | Endpoint Wasabi S3 | `https://s3.wasabisys.com` |
| `HSA_OVERRIDE_GFX_VERSION` | Version GFX pour RX 6600 | `10.3.0` |

### 4. Déploiement

1. **Poussez le code** sur votre repository Git
2. **Dans Coolify** (accessible via `http://votre-ip:8000`):
   - Cliquez sur "Create New Resource"
   - Sélectionnez "Application"
   - Choisissez votre repository
   - Configurez les variables d'environnement
   - Ajoutez la configuration GPU Passthrough
   - Cliquez sur "Deploy"

### 5. Vérification du GPU

Une fois déployé, vérifiez les logs dans Coolify. Vous devriez voir :

```
✅ GPU disponible: AMD Radeon RX 6600
   Nombre de GPU: 1
   Version PyTorch: 2.3.0
   Version ROCm/HIP: 6.1.0
```

Si vous voyez `"GPU Available: True"`, PureVolley est officiellement "vivant" sur votre matériel !

## 🐳 Exécution Locale (Développement)

### 1. Construction de l'image

```bash
cd purevolley-worker
docker build -t purevolley-worker:latest .
```

### 2. Exécution avec GPU

```bash
# Créer un fichier .env avec vos variables
cp .env.example .env
# Éditer .env avec vos valeurs

# Exécuter le conteneur avec GPU
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --group-add render \
  --env-file .env \
  purevolley-worker:latest
```

### 3. Test manuel

```bash
# Exécuter le worker directement (sans Docker)
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
python worker.py
```

## 📊 Structure de la Base de Données

### Table `matches`

```sql
CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_url TEXT NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Statuts possibles

- `pending`: Match en attente de traitement
- `processing`: En cours de traitement
- `completed`: Traitement terminé avec succès
- `failed`: Échec du traitement

## 🔧 Développement

### Ajout de fonctionnalités IA

Le worker est conçu pour être facilement étendu avec des modèles IA réels :

1. **VideoMAE pour la détection d'actions** :
   ```python
   # Dans process_video(), remplacer la simulation par :
   from transformers import VideoMAEForVideoClassification
   model = VideoMAEForVideoClassification.from_pretrained("MCG-NJU/videomae-base")
   ```

2. **YOLO pour la détection de joueurs** :
   ```python
   from ultralytics import YOLO
   model = YOLO('yolov8n.pt')
   results = model(video_path)
   ```

### Tests

```bash
# Test unitaire
python -m pytest tests/

# Test d'intégration
python test_integration.py
```

## 🐛 Dépannage

### Problème: GPU non détecté

**Solution**:
1. Vérifiez que ROCm 6.1 est installé sur l'hôte
2. Vérifiez la variable `HSA_OVERRIDE_GFX_VERSION=10.3.0`
3. Vérifiez les permissions des devices `/dev/kfd` et `/dev/dri`

### Problème: Erreur de connexion à Supabase

**Solution**:
1. Vérifiez les variables `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY`
2. Vérifiez que le service role a les permissions nécessaires
3. Vérifiez la connectivité réseau

### Problème: Erreur S3

**Solution**:
1. Vérifiez les clés Wasabi S3
2. Vérifiez que le bucket existe et est accessible
3. Vérifiez les permissions IAM

## 📈 Monitoring

### Logs

Les logs sont disponibles :
- Dans la sortie console du conteneur
- Dans le fichier `worker.log` local
- Sur Wasabi S3 dans le dossier `logs/`

### Métriques

Le worker expose des métriques via :
- Temps de traitement par vidéo
- Taux de réussite/échec
- Utilisation GPU/CPU

## 🤝 Contribution

1. Fork le repository
2. Créez une branche feature (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add amazing feature'`)
4. Pushez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [ROCm](https://rocm.docs.amd.com/) pour le support GPU AMD
- [PyTorch](https://pytorch.org/) pour le framework d'IA
- [Supabase](https://supabase.com/) pour le backend
- [Wasabi](https://wasabi.com/) pour le stockage S3
- [Coolify](https://coolify.io/) pour le déploiement