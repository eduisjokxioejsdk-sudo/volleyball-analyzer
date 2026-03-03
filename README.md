# 🏐 CourtVision - Volleyball Video Analyzer

Analyse automatique de vidéos de volleyball basée sur [VolleyVision](https://github.com/shukkkur/VolleyVision).

## Fonctionnalités

- 🔍 **Détection d'actions** : Détecte les services, spikes, blocks, défenses et sets
- 🎯 **Détection d'événements** : Filtre temporel (sliding window) pour confirmer les événements
- ✂️ **Découpage en rallyes** : Segmente automatiquement la vidéo en points individuels
- 📊 **Attribution du score** : Heuristique automatique pour attribuer les points
- 🎬 **Export de clips** : Génère des clips vidéo annotés pour chaque rallye
- 📄 **Résultats JSON** : Export structuré de toutes les données d'analyse

## Prérequis

- Python 3.9+
- [VolleyVision](https://github.com/shukkkur/VolleyVision) cloné dans le dossier parent

## Installation

```bash
# 1. Cloner VolleyVision (modèles YOLOv8 inclus)
cd CourtVision
git clone --depth 1 https://github.com/shukkkur/VolleyVision.git

# 2. Installer les dépendances
cd volleyball-analyzer
pip install -r requirements.txt
```

## Utilisation

### Analyse basique
```bash
python analyze_video.py --video chemin/vers/match.mp4
```

### Avec options
```bash
python analyze_video.py \
  --video match.mp4 \
  --output_dir Resultats \
  --conf 0.3 \
  --team_left "Paris" \
  --team_right "Lyon" \
  --gpu
```

### Options disponibles

| Option | Description | Défaut |
|--------|-------------|--------|
| `--video` | Chemin vers la vidéo | (obligatoire) |
| `--output_dir` | Dossier de sortie | `Output` |
| `--conf` | Seuil de confiance (0-1) | `0.4` |
| `--imgsz W H` | Taille d'inférence | auto |
| `--gpu` | Utiliser le GPU | non |
| `--team_left` | Nom équipe gauche | `Équipe A` |
| `--team_right` | Nom équipe droite | `Équipe B` |

## Résultats

L'analyse génère :

```
Output/
├── analysis_results.json    # Données structurées complètes
└── rally_clips/             # Clips vidéo par rallye
    ├── rally_001_00-12.3_Équipe A.mp4
    ├── rally_002_00-28.5_Équipe B.mp4
    └── ...
```

### Structure du JSON

```json
{
  "video": { "filename": "match.mp4", "fps": 30, "duration": 3600, ... },
  "teams": { "left": "Paris", "right": "Lyon" },
  "score": { "Paris": 25, "Lyon": 22 },
  "events": [
    { "time_str": "00:12.3", "action": "serve", "side": "left", ... },
    { "time_str": "00:15.7", "action": "spike", "side": "right", ... }
  ],
  "rallies": [
    {
      "rally_num": 1,
      "start_time_str": "00:11.0",
      "end_time_str": "00:18.5",
      "scored_by": "Paris",
      "score_after": { "Paris": 1, "Lyon": 0 },
      "events": [...]
    }
  ],
  "statistics": { "total_rallies": 47, "avg_rally_duration": 8.3, ... }
}
```

## Architecture

```
CourtVision/
├── VolleyVision/                    # Repo VolleyVision (modèles)
│   └── Stage II - Players & Actions/
│       ├── actions/yV8_medium/weights/best.pt   # Modèle actions
│       └── players/yV8_medium/weights/best.pt   # Modèle joueurs
├── volleyball-analyzer/             # Ce projet
│   ├── analyze_video.py             # Script principal d'analyse
│   ├── api_server.py                # API REST (pour intégration web)
│   ├── requirements.txt
│   └── README.md
└── courtvisionpro-main/             # Frontend web
```

## Pipeline d'analyse

1. **Phase 1** - Parcourt chaque frame et détecte les actions (YOLOv8)
2. **Phase 2** - Fenêtre glissante pour confirmer les événements temporels
3. **Phase 3** - Découpage en rallyes + attribution automatique du score
4. **Phase 4** - Export JSON + clips vidéo annotés

## Heuristique de scoring

L'attribution automatique du score utilise les règles suivantes :
- **Spike en fin de rallye** → L'attaquant a marqué
- **Block en fin de rallye** → Le bloqueur a marqué
- **Défense en fin de rallye** → L'autre côté a marqué (la balle est tombée)
- **Service sans suite** → Ace probable, le serveur a marqué

> ⚠️ Cette heuristique est approximative. Pour un scoring précis, les résultats JSON permettent une correction manuelle facile.

## Modèles utilisés

| Modèle | Classes | mAP50 | Précision | Rappel |
|--------|---------|-------|-----------|--------|
| Actions (YOLOv8m) | block, defense, serve, set, spike | 92.3% | 92.4% | 89.4% |
| Joueurs (YOLOv8m) | player | 97.2% | 94.2% | 94.0% |

## Crédits

- [VolleyVision](https://github.com/shukkkur/VolleyVision) par shukkkur
- Modèles entraînés sur des datasets de [RoboFlow](https://roboflow.com)
