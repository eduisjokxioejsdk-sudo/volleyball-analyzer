#!/usr/bin/env python3
"""
CourtVision - Volleyball Video Analyzer
========================================
Utilise les modèles YOLOv8 de VolleyVision pour :
1. Détecter les actions de volleyball (serve, spike, block, defense, set)
2. Découper la vidéo en rallyes (points)
3. Attribuer automatiquement le score
4. Suivre les rotations du passeur (P1→P6→P5→P4→P3→P2)

Usage:
    python analyze_video.py --video path/to/video.mp4 [--output_dir Output]
"""

import os
import sys
import json
import argparse
import warnings
from datetime import timedelta
from collections import deque, Counter
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

warnings.filterwarnings("ignore")

# ==============================================================================
# Configuration
# ==============================================================================

# Chemin vers les poids du modèle d'actions (relatif à VolleyVision)
VOLLEYVISION_DIR = os.path.join(os.path.dirname(__file__), "..", "VolleyVision")
ACTIONS_MODEL_PATH = os.path.join(
    VOLLEYVISION_DIR, "Stage II - Players & Actions", "actions", "yV8_medium", "weights", "best.pt"
)
PLAYERS_MODEL_PATH = os.path.join(
    VOLLEYVISION_DIR, "Stage II - Players & Actions", "players", "yV8_medium", "weights", "best.pt"
)

# Classes d'actions détectées par le modèle
ACTION_CLASSES = {0: 'block', 1: 'defense', 2: 'serve', 3: 'set', 4: 'spike'}
ACTION_COLORS = {
    'block': (255, 0, 0),       # Bleu
    'defense': (0, 255, 0),     # Vert
    'serve': (0, 255, 255),     # Jaune
    'set': (255, 165, 0),       # Orange
    'spike': (0, 0, 255),       # Rouge
}

# Paramètres de détection d'événements (sliding window)
SLIDING_WINDOW_SIZE = 10        # Taille de la fenêtre glissante (en nb de frames analysées)
EVENT_THRESHOLD = 3             # Nb de détections nécessaires pour déclarer un événement

# Paramètres de découpage des rallyes
INACTIVITY_SECONDS = 4.0        # Secondes sans action YOLO = fin du rallye
MIN_RALLY_SECONDS = 3.0         # Durée minimale d'un rallye valide (ignore les faux services)
RALLY_END_BUFFER = 1.5          # Secondes de buffer après la dernière action détectée
RALLY_START_BUFFER = 1.0        # Secondes de buffer avant le service

# Paramètres de scoring
FRAME_CENTER_RATIO = 0.5        # Ratio pour séparer les deux côtés du terrain

# Ordre des rotations du passeur en volleyball
# P1 → P6 → P5 → P4 → P3 → P2 → P1 ...
ROTATION_ORDER = ['P1', 'P6', 'P5', 'P4', 'P3', 'P2']


# ==============================================================================
# Gestionnaire de Rotations
# ==============================================================================

class RotationTracker:
    """
    Suit les rotations du passeur pour chaque équipe.
    
    En volleyball, les rotations fonctionnent ainsi :
    - Quand l'équipe en réception gagne le point (side-out), elle récupère
      le service ET ses joueurs tournent d'une position.
    - Quand l'équipe au service gagne le point, pas de rotation.
    - Ordre des positions du passeur : P1 → P6 → P5 → P4 → P3 → P2 → P1...
    """

    def __init__(self, team_left, team_right,
                 setter_start_left='P1', setter_start_right='P1',
                 first_serve='left'):
        self.team_left = team_left
        self.team_right = team_right

        # Position initiale du passeur pour chaque équipe (index dans ROTATION_ORDER)
        self.rotation_index = {
            team_left: ROTATION_ORDER.index(setter_start_left),
            team_right: ROTATION_ORDER.index(setter_start_right),
        }

        # Quelle équipe sert actuellement
        self.serving_team = team_left if first_serve == 'left' else team_right

        # Historique des rotations
        self.history = []

    def get_setter_position(self, team):
        """Retourne la position actuelle du passeur pour une équipe."""
        idx = self.rotation_index[team]
        return ROTATION_ORDER[idx]

    def get_serving_team(self):
        """Retourne l'équipe actuellement au service."""
        return self.serving_team

    def get_receiving_team(self):
        """Retourne l'équipe actuellement en réception."""
        if self.serving_team == self.team_left:
            return self.team_right
        return self.team_left

    def process_point(self, scored_by, rally_num=0):
        """
        Traite un point marqué et met à jour les rotations.
        
        Règles :
        - Si l'équipe en réception marque (side-out) → elle récupère le service
          ET tourne d'une position AVANT de servir.
        - Si l'équipe au service marque → pas de rotation, elle continue à servir.
        """
        receiving_team = self.get_receiving_team()
        rotated = False
        rotation_team = None

        if scored_by == receiving_team:
            # SIDE-OUT : l'équipe en réception a marqué
            # 1. Elle récupère le service
            self.serving_team = scored_by
            # 2. Elle tourne d'une position
            self._rotate(scored_by)
            rotated = True
            rotation_team = scored_by
        # Si l'équipe au service a marqué → pas de changement

        # Enregistrer dans l'historique
        entry = {
            'rally_num': rally_num,
            'scored_by': scored_by,
            'serving_team': self.serving_team,
            'rotated': rotated,
            'rotation_team': rotation_team,
            'setter_left': self.get_setter_position(self.team_left),
            'setter_right': self.get_setter_position(self.team_right),
        }
        self.history.append(entry)

        return entry

    def _rotate(self, team):
        """Fait tourner une équipe d'une position."""
        self.rotation_index[team] = (self.rotation_index[team] + 1) % len(ROTATION_ORDER)

    def get_state(self):
        """Retourne l'état actuel des rotations."""
        return {
            'serving_team': self.serving_team,
            'setter_positions': {
                self.team_left: self.get_setter_position(self.team_left),
                self.team_right: self.get_setter_position(self.team_right),
            }
        }


# ==============================================================================
# Classe principale d'analyse
# ==============================================================================

class VolleyballAnalyzer:
    """Analyse une vidéo de volleyball pour détecter les rallyes et attribuer le score."""

    def __init__(self, video_path, output_dir="Output", confidence=0.4, 
                 img_size=640, use_gpu=False, frame_skip=15,
                 team_left="Équipe A", team_right="Équipe B",
                 setter_start_left='P1', setter_start_right='P1',
                 first_serve='left'):
        self.video_path = video_path
        self.output_dir = output_dir
        self.confidence = confidence
        self.img_size = img_size
        self.use_gpu = use_gpu
        self.frame_skip = max(1, frame_skip)
        self.team_left = team_left
        self.team_right = team_right

        # Résultats
        self.frame_actions = []     # Actions détectées par frame (analysées)
        self.frame_index = {}       # Mapping frame_num → index dans frame_actions
        self.events = []            # Événements détectés (temporel)
        self.rallies = []           # Rallyes découpés
        self.score = {team_left: 0, team_right: 0}

        # Gestionnaire de rotations
        self.rotation_tracker = RotationTracker(
            team_left=team_left,
            team_right=team_right,
            setter_start_left=setter_start_left,
            setter_start_right=setter_start_right,
            first_serve=first_serve,
        )

        # Charger le modèle
        self._load_model()

        # Ouvrir la vidéo
        self._open_video()

    def _load_model(self):
        """Charge le modèle YOLOv8 d'actions (local, pas d'API)."""
        try:
            from ultralytics import YOLO
        except ImportError:
            print("❌ Erreur: ultralytics non installé. Lancez: pip install ultralytics")
            sys.exit(1)

        # Vérifier que les poids existent
        if not os.path.exists(ACTIONS_MODEL_PATH):
            raise FileNotFoundError(
                f"Modèle non trouvé à: {ACTIONS_MODEL_PATH}. "
                f"Assurez-vous d'avoir cloné VolleyVision dans: {VOLLEYVISION_DIR}"
            )

        print(f"📦 Chargement du modèle d'actions: {os.path.basename(ACTIONS_MODEL_PATH)}")
        print(f"   (YOLOv8m local - pas d'API RoboFlow)")
        self.action_model = YOLO(ACTIONS_MODEL_PATH)

        # Charger aussi le modèle de joueurs si disponible
        self.player_model = None
        if os.path.exists(PLAYERS_MODEL_PATH):
            print(f"📦 Chargement du modèle de joueurs: {os.path.basename(PLAYERS_MODEL_PATH)}")
            self.player_model = YOLO(PLAYERS_MODEL_PATH)

        if self.use_gpu:
            import torch
            if torch.cuda.is_available():
                print("🖥️  GPU CUDA détecté - utilisation du GPU")
            else:
                print("⚠️  GPU non disponible - utilisation du CPU")

    def _open_video(self):
        """Ouvre la vidéo et récupère ses propriétés."""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Impossible d'ouvrir la vidéo: {self.video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        # Nombre de frames qui seront réellement analysées
        self.analyzed_frames_count = (self.total_frames + self.frame_skip - 1) // self.frame_skip

        print(f"\n🎬 Vidéo: {os.path.basename(self.video_path)}")
        print(f"   Résolution: {self.frame_width}x{self.frame_height}")
        print(f"   FPS: {self.fps:.1f}")
        print(f"   Frames totales: {self.total_frames}")
        print(f"   Durée: {timedelta(seconds=int(self.duration))}")
        print(f"   ⚡ Frame skip: 1/{self.frame_skip} → {self.analyzed_frames_count} frames analysées "
              f"(au lieu de {self.total_frames}, {self.frame_skip}x plus rapide)")

    def frame_to_time(self, frame_num):
        """Convertit un numéro de frame en temps (secondes)."""
        return frame_num / self.fps if self.fps > 0 else 0

    def time_to_str(self, seconds):
        """Convertit des secondes en format mm:ss.ms"""
        return str(timedelta(seconds=round(seconds, 1)))[2:10]

    # ==========================================================================
    # Phase 1: Détection des actions avec frame skipping
    # ==========================================================================

    def detect_actions(self, progress_callback=None):
        """Parcourt la vidéo et détecte les actions (avec frame skipping).
        
        Args:
            progress_callback: callable(percent: int) called with real progress 0-100
        """
        print(f"\n🔍 Phase 1: Détection des actions (1 frame sur {self.frame_skip})...")

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.frame_actions = []
        self.frame_index = {}

        pbar = tqdm(total=self.analyzed_frames_count, desc="Détection", unit="frame",
                     bar_format='{l_bar}{bar:30}{r_bar}')

        frame_num = 0
        analyzed_count = 0
        last_reported_percent = -1
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            # Frame skipping : analyser seulement 1 frame sur N
            if frame_num % self.frame_skip == 0:
                # Prédiction avec YOLOv8
                predict_kwargs = {
                    'conf': self.confidence,
                    'verbose': False,
                }
                if self.img_size:
                    predict_kwargs['imgsz'] = self.img_size

                results = self.action_model.predict(frame, **predict_kwargs)

                # Extraire les détections
                detections = []
                boxes = results[0].boxes
                if len(boxes) > 0:
                    for box in boxes:
                        x_min, y_min, x_max, y_max = box.xyxy[0].cpu().numpy()
                        cls_id = int(box.cls.cpu())
                        conf = float(box.conf.cpu())
                        center_x = (x_min + x_max) / 2
                        center_y = (y_min + y_max) / 2
                        action_name = ACTION_CLASSES.get(cls_id, 'unknown')

                        detections.append({
                            'action': action_name,
                            'confidence': conf,
                            'bbox': [float(x_min), float(y_min), float(x_max), float(y_max)],
                            'center': [float(center_x), float(center_y)],
                            'side': 'left' if center_x < self.frame_width * FRAME_CENTER_RATIO else 'right',
                            'class_id': cls_id,
                        })

                entry = {
                    'frame': frame_num,
                    'time': self.frame_to_time(frame_num),
                    'detections': detections,
                }
                self.frame_index[frame_num] = len(self.frame_actions)
                self.frame_actions.append(entry)

                analyzed_count += 1
                pbar.update(1)

                # Report real progress via callback (every 2%)
                if progress_callback and self.analyzed_frames_count > 0:
                    percent = int((analyzed_count / self.analyzed_frames_count) * 100)
                    if percent != last_reported_percent and percent % 2 == 0:
                        last_reported_percent = percent
                        try:
                            progress_callback(percent)
                        except Exception:
                            pass

            frame_num += 1

        pbar.close()

        # Statistiques
        total_detections = sum(len(f['detections']) for f in self.frame_actions)
        action_counts = Counter()
        for f in self.frame_actions:
            for d in f['detections']:
                action_counts[d['action']] += 1

        print(f"\n📊 Résultats de détection:")
        print(f"   Frames analysées: {analyzed_count}/{self.total_frames} (skip={self.frame_skip})")
        print(f"   Total détections: {total_detections}")
        for action, count in action_counts.most_common():
            print(f"   - {action}: {count} détections")

        return self.frame_actions

    # ==========================================================================
    # Phase 2: Détection d'événements par fenêtre glissante
    # ==========================================================================

    def detect_events(self):
        """Utilise la fenêtre glissante pour détecter les événements."""
        print(f"\n🎯 Phase 2: Détection d'événements (fenêtre glissante)...")

        self.events = []
        sliding_window = deque(maxlen=SLIDING_WINDOW_SIZE)
        last_event = None
        last_event_frame = -999

        # Ajuster le min_gap en tenant compte du frame_skip
        min_gap_seconds = 1.0
        min_gap_frames = max(1, int(min_gap_seconds * self.fps / self.frame_skip))

        for idx, frame_data in enumerate(self.frame_actions):
            frame_num = frame_data['frame']
            detections = frame_data['detections']

            if detections:
                # Ajouter les actions détectées à la fenêtre
                for d in detections:
                    sliding_window.append(d['action'])

                # Vérifier si un événement se déclare (ignorer les None)
                counter = Counter(x for x in sliding_window if x is not None)
                if not counter:
                    frame_num += 1
                    continue
                most_common_action, count = counter.most_common(1)[0]

                if count >= EVENT_THRESHOLD:
                    # Éviter les doublons
                    if (most_common_action != last_event or 
                        idx - last_event_frame > min_gap_frames):

                        # Trouver la position moyenne de cet événement
                        start_idx = max(0, idx - SLIDING_WINDOW_SIZE)
                        event_detections = [
                            d for f in self.frame_actions[start_idx:idx + 1]
                            for d in f['detections']
                            if d['action'] == most_common_action
                        ]
                        avg_x = np.mean([d['center'][0] for d in event_detections]) if event_detections else self.frame_width / 2
                        avg_y = np.mean([d['center'][1] for d in event_detections]) if event_detections else self.frame_height / 2

                        event = {
                            'frame': frame_num,
                            'time': self.frame_to_time(frame_num),
                            'time_str': self.time_to_str(self.frame_to_time(frame_num)),
                            'action': most_common_action,
                            'count': count,
                            'position': [float(avg_x), float(avg_y)],
                            'side': 'left' if avg_x < self.frame_width * FRAME_CENTER_RATIO else 'right',
                        }
                        self.events.append(event)

                        last_event = most_common_action
                        last_event_frame = idx

                        # Reset la fenêtre après un événement détecté
                        sliding_window.clear()
            else:
                sliding_window.append(None)

        print(f"\n📊 Événements détectés: {len(self.events)}")
        event_counts = Counter(e['action'] for e in self.events)
        for action, count in event_counts.most_common():
            print(f"   - {action}: {count} événements")

        # Afficher la timeline
        print(f"\n📋 Timeline des événements:")
        for e in self.events:
            side_emoji = "⬅️" if e['side'] == 'left' else "➡️"
            print(f"   {e['time_str']} | {side_emoji} {e['action'].upper():>8} (x{e['count']}, côté {e['side']})")

        return self.events

    # ==========================================================================
    # Phase 3: Découpage en rallyes et attribution du score + rotations
    # ==========================================================================

    def detect_rallies(self):
        """Découpe la vidéo en rallyes basés sur les événements détectés."""
        print(f"\n🏐 Phase 3: Découpage en rallyes, score et rotations...")

        if not self.events:
            print("   ⚠️ Aucun événement détecté - impossible de découper en rallyes")
            return []

        self.rallies = []
        inactivity_seconds = INACTIVITY_SECONDS
        # Convertir en nombre de frames analysées (pas de frames brutes)
        inactivity_analyzed = max(1, int(inactivity_seconds * self.fps / self.frame_skip))
        min_rally_analyzed = max(1, int(MIN_RALLY_SECONDS * self.fps / self.frame_skip))

        # ======================================================================
        # Méthode 1: Basée sur les services détectés
        # ======================================================================
        raw_serves = [e for e in self.events if e['action'] == 'serve']

        # Dédupliquer les services trop proches (même service détecté plusieurs fois)
        serves = self._deduplicate_serves(raw_serves)

        if serves:
            print(f"   🎾 {len(raw_serves)} services bruts → {len(serves)} services uniques (après déduplication)")
            self._rally_detection_from_serves(serves)
        else:
            print(f"   ⚠️ Aucun service détecté - découpage basé sur les périodes d'activité")
            self._rally_detection_from_activity()

        # Attribution du score + rotations
        self._attribute_scores_and_rotations()

        print(f"\n📊 Résumé:")
        print(f"   Rallyes détectés: {len(self.rallies)}")
        print(f"   Score final: {self.team_left} {self.score[self.team_left]} - {self.score[self.team_right]} {self.team_right}")
        state = self.rotation_tracker.get_state()
        print(f"   🔄 Passeur {self.team_left}: {state['setter_positions'][self.team_left]}")
        print(f"   🔄 Passeur {self.team_right}: {state['setter_positions'][self.team_right]}")

        return self.rallies

    def _deduplicate_serves(self, raw_serves, min_gap_seconds=6.0):
        """
        Fusionne les services détectés trop proches les uns des autres.
        
        Si deux services sont à moins de min_gap_seconds l'un de l'autre,
        on ne garde que le premier (c'est probablement le même service
        détecté plusieurs fois par l'IA).
        
        Un vrai point de volleyball dure au minimum ~5-6 secondes
        (service + réception + attaque), donc 12s de gap minimum est safe.
        """
        if not raw_serves:
            return []
        
        deduplicated = [raw_serves[0]]
        
        for serve in raw_serves[1:]:
            last_serve = deduplicated[-1]
            gap_seconds = (serve['frame'] - last_serve['frame']) / self.fps if self.fps > 0 else 999
            
            if gap_seconds >= min_gap_seconds:
                deduplicated.append(serve)
            else:
                # Service trop proche du précédent → on l'ignore (doublon)
                pass
        
        return deduplicated

    def _rally_detection_from_serves(self, serves):
        """
        Détecte les rallyes en se basant sur les services.
        
        Logique améliorée :
        - Début du point = frame du service
        - Fin du point   = premier GAP d'inactivité (3s sans détection YOLO)
        
        Cela évite d'inclure les temps morts (célébrations, marche, etc.)
        qui sont souvent détectés comme des fausses actions par YOLO.
        """
        # Gap d'inactivité qui marque la fin du rallye (en secondes)
        INACTIVITY_GAP = 3.0
        # Nombre minimum de détections pour qu'une frame "compte" comme active
        # (filtre le bruit : 1 détection isolée = probablement pas du jeu actif)
        MIN_DETECTIONS_ACTIVE = 1

        inactivity_gap_frames = int(INACTIVITY_GAP * self.fps)

        for i, serve in enumerate(serves):
            # Début du point : directement au service
            rally_start_frame = serve['frame']

            # Borne max = le service suivant (ou fin de vidéo)
            if i + 1 < len(serves):
                next_serve_frame = serves[i + 1]['frame']
            else:
                next_serve_frame = self.total_frames

            # ============================================================
            # Trouver la fin du rallye par détection de gap d'inactivité
            # ============================================================
            # On parcourt les frame_actions après le service.
            # On cherche le PREMIER trou >= INACTIVITY_GAP sans détection.
            # Le point se termine à la dernière détection avant ce trou.
            
            last_active_frame = rally_start_frame
            rally_end_frame = None
            
            for f in self.frame_actions:
                if f['frame'] < rally_start_frame:
                    continue
                if f['frame'] >= next_serve_frame:
                    break
                
                if f['detections'] and len(f['detections']) >= MIN_DETECTIONS_ACTIVE:
                    # Vérifier s'il y a eu un gap AVANT cette détection
                    gap = f['frame'] - last_active_frame
                    if gap > inactivity_gap_frames and last_active_frame > rally_start_frame:
                        # GAP trouvé ! Le rallye s'est terminé à last_active_frame
                        rally_end_frame = last_active_frame
                        break
                    # Mettre à jour la dernière frame active
                    last_active_frame = f['frame']
            
            # Si pas de gap trouvé, utiliser la dernière frame active
            if rally_end_frame is None:
                rally_end_frame = last_active_frame

            # Ne pas dépasser le service suivant ni la fin de vidéo
            rally_end_frame = min(rally_end_frame, next_serve_frame - 1, self.total_frames)

            # Durée minimale : au moins MIN_RALLY_SECONDS
            rally_end_frame = max(rally_end_frame, rally_start_frame + int(self.fps * MIN_RALLY_SECONDS))
            rally_end_frame = min(rally_end_frame, self.total_frames)

            # Vérifier la durée minimale
            min_rally_frames = int(MIN_RALLY_SECONDS * self.fps)
            if rally_end_frame - rally_start_frame < min_rally_frames:
                continue

            # Collecter les événements de ce rallye
            rally_events = [
                e for e in self.events
                if rally_start_frame <= e['frame'] <= rally_end_frame
            ]

            rally = {
                'rally_num': len(self.rallies) + 1,
                'start_frame': rally_start_frame,
                'end_frame': rally_end_frame,
                'start_time': self.frame_to_time(rally_start_frame),
                'end_time': self.frame_to_time(rally_end_frame),
                'start_time_str': self.time_to_str(self.frame_to_time(rally_start_frame)),
                'end_time_str': self.time_to_str(self.frame_to_time(rally_end_frame)),
                'duration': self.frame_to_time(rally_end_frame - rally_start_frame),
                'events': rally_events,
                'serve_side': serve['side'],
                'scored_by': None,
                'rotation': None,
            }
            self.rallies.append(rally)
            
            # Log pour debug
            gap_info = f"(gap@{self.time_to_str(self.frame_to_time(rally_end_frame))})" if rally_end_frame < next_serve_frame - 1 else "(→next serve)"
            print(f"   Point {rally['rally_num']}: {rally['start_time_str']}-{rally['end_time_str']} "
                  f"({rally['duration']:.1f}s) {gap_info}")

    def _rally_detection_from_activity(self):
        """Détecte les rallyes basés sur les périodes d'activité/inactivité."""
        inactivity_frames = int(INACTIVITY_SECONDS * self.fps)
        min_rally_frames = int(MIN_RALLY_SECONDS * self.fps)

        # Trouver les frames actives
        active_frames = []
        for f in self.frame_actions:
            if f['detections']:
                active_frames.append(f['frame'])

        if not active_frames:
            return

        # Grouper les frames actives en segments continus
        segments = []
        current_start = active_frames[0]
        current_end = active_frames[0]

        for frame in active_frames[1:]:
            if frame - current_end <= inactivity_frames:
                current_end = frame
            else:
                if current_end - current_start >= min_rally_frames:
                    segments.append((current_start, current_end))
                current_start = frame
                current_end = frame

        # Dernier segment
        if current_end - current_start >= min_rally_frames:
            segments.append((current_start, current_end))

        # Créer les rallyes
        for start, end in segments:
            start_frame = max(0, start - int(self.fps * 1))
            end_frame = min(self.total_frames, end + int(self.fps * 1))

            rally_events = [
                e for e in self.events
                if start_frame <= e['frame'] <= end_frame
            ]

            rally = {
                'rally_num': len(self.rallies) + 1,
                'start_frame': start_frame,
                'end_frame': end_frame,
                'start_time': self.frame_to_time(start_frame),
                'end_time': self.frame_to_time(end_frame),
                'start_time_str': self.time_to_str(self.frame_to_time(start_frame)),
                'end_time_str': self.time_to_str(self.frame_to_time(end_frame)),
                'duration': self.frame_to_time(end_frame - start_frame),
                'events': rally_events,
                'serve_side': rally_events[0]['side'] if rally_events else 'unknown',
                'scored_by': None,
                'rotation': None,
            }
            self.rallies.append(rally)

    def _find_rally_end(self, start_frame, max_frame):
        """Trouve la frame de fin du rallye par détection d'inactivité."""
        inactivity_frames = int(INACTIVITY_SECONDS * self.fps)
        last_active_frame = start_frame

        for f in self.frame_actions:
            if f['frame'] < start_frame:
                continue
            if f['frame'] > max_frame:
                break
            if f['detections']:
                last_active_frame = f['frame']
            elif f['frame'] - last_active_frame > inactivity_frames:
                return last_active_frame + int(self.fps * 0.5)

        return min(last_active_frame + int(self.fps * 1), max_frame)

    def _attribute_scores_and_rotations(self):
        """Attribue le score ET met à jour les rotations pour chaque rallye."""
        print(f"\n🎯 Attribution automatique du score et des rotations...")

        self.score = {self.team_left: 0, self.team_right: 0}

        for rally in self.rallies:
            events = rally['events']
            if not events:
                rally['scored_by'] = 'unknown'
                rally['rotation'] = self.rotation_tracker.get_state()
                continue

            # =================================================================
            # Heuristique de scoring
            # =================================================================
            # 1. Chercher la dernière action offensive (spike ou block)
            # 2. Spike → l'attaquant a probablement marqué
            # 3. Block → le bloqueur a probablement marqué
            # 4. Defense en dernier → le défenseur n'a PAS marqué (balle tombée de son côté)
            
            last_offensive = None
            for e in reversed(events):
                if e['action'] in ('spike', 'block'):
                    last_offensive = e
                    break

            if last_offensive:
                if last_offensive['side'] == 'left':
                    rally['scored_by'] = self.team_left
                else:
                    rally['scored_by'] = self.team_right
            else:
                last_event = events[-1]
                if last_event['action'] == 'defense':
                    # Défense en dernier = l'autre côté a marqué
                    if last_event['side'] == 'left':
                        rally['scored_by'] = self.team_right
                    else:
                        rally['scored_by'] = self.team_left
                elif last_event['action'] == 'serve':
                    # Ace probable
                    rally['scored_by'] = self.team_left if last_event['side'] == 'left' else self.team_right
                else:
                    rally['scored_by'] = self.team_left if last_event['side'] == 'left' else self.team_right

            # =================================================================
            # Mise à jour du score
            # =================================================================
            if rally['scored_by'] in self.score:
                self.score[rally['scored_by']] += 1
            rally['score_after'] = dict(self.score)

            # =================================================================
            # Mise à jour des rotations du passeur
            # =================================================================
            rotation_entry = self.rotation_tracker.process_point(
                scored_by=rally['scored_by'],
                rally_num=rally['rally_num']
            )
            rally['rotation'] = {
                'serving_team': rotation_entry['serving_team'],
                'rotated': rotation_entry['rotated'],
                'rotation_team': rotation_entry['rotation_team'],
                'setter_left': rotation_entry['setter_left'],
                'setter_right': rotation_entry['setter_right'],
            }

        # Afficher le score rallye par rallye avec rotations
        print(f"\n📋 Score et rotations rallye par rallye:")
        print(f"   {'Rally':>7} | {'Temps':>15} | {'Point':>12} | {'Score':>20} | {'Service':>12} | {'Rotation':>8} | {'Passeur G':>9} | {'Passeur D':>9}")
        print(f"   {'-'*7} | {'-'*15} | {'-'*12} | {'-'*20} | {'-'*12} | {'-'*8} | {'-'*9} | {'-'*9}")
        for rally in self.rallies:
            rot = rally.get('rotation', {})
            score_str = f"{self.score.get(self.team_left, 0) if not rally.get('score_after') else rally['score_after'].get(self.team_left, 0)}-{self.score.get(self.team_right, 0) if not rally.get('score_after') else rally['score_after'].get(self.team_right, 0)}"
            rotated_str = f"🔄 {rot.get('rotation_team', '')[:6]}" if rot.get('rotated') else "  -"
            print(f"   Rally {rally['rally_num']:>2} | {rally['start_time_str']}-{rally['end_time_str']} | "
                  f"{rally['scored_by']:<12} | {self.team_left} {score_str} {self.team_right} | "
                  f"{rot.get('serving_team', '?'):<12} | {rotated_str:<8} | "
                  f"{rot.get('setter_left', '?'):<9} | {rot.get('setter_right', '?'):<9}")

    # ==========================================================================
    # Phase 4: Export des résultats
    # ==========================================================================

    def export_results(self):
        """Exporte les résultats en JSON et découpe la vidéo en clips."""
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Export JSON
        self._export_json()

        # 2. Découper les rallyes en clips vidéo
        self._export_rally_clips()

        print(f"\n✅ Résultats exportés dans: {self.output_dir}")

    def _export_json(self):
        """Exporte les résultats d'analyse en JSON."""
        output_path = os.path.join(self.output_dir, "analysis_results.json")

        state = self.rotation_tracker.get_state()

        results = {
            'video': {
                'path': self.video_path,
                'filename': os.path.basename(self.video_path),
                'fps': self.fps,
                'total_frames': self.total_frames,
                'analyzed_frames': len(self.frame_actions),
                'frame_skip': self.frame_skip,
                'width': self.frame_width,
                'height': self.frame_height,
                'duration': self.duration,
                'duration_str': str(timedelta(seconds=int(self.duration))),
            },
            'settings': {
                'confidence': self.confidence,
                'frame_skip': self.frame_skip,
                'sliding_window_size': SLIDING_WINDOW_SIZE,
                'event_threshold': EVENT_THRESHOLD,
                'inactivity_seconds': INACTIVITY_SECONDS,
            },
            'teams': {
                'left': self.team_left,
                'right': self.team_right,
            },
            'score': self.score,
            'rotations': {
                'current_serving_team': state['serving_team'],
                'setter_positions': state['setter_positions'],
                'history': self.rotation_tracker.history,
            },
            'events': self.events,
            'rallies': [
                {
                    'rally_num': r['rally_num'],
                    'start_time': r['start_time'],
                    'end_time': r['end_time'],
                    'start_time_str': r['start_time_str'],
                    'end_time_str': r['end_time_str'],
                    'duration': r['duration'],
                    'start_frame': r['start_frame'],
                    'end_frame': r['end_frame'],
                    'serve_side': r['serve_side'],
                    'scored_by': r['scored_by'],
                    'score_after': r.get('score_after', {}),
                    'rotation': r.get('rotation', {}),
                    'events': r['events'],
                }
                for r in self.rallies
            ],
            'statistics': {
                'total_rallies': len(self.rallies),
                'total_events': len(self.events),
                'events_by_type': dict(Counter(e['action'] for e in self.events)),
                'avg_rally_duration': float(np.mean([r['duration'] for r in self.rallies])) if self.rallies else 0,
                'speed_factor': f"{self.frame_skip}x (1 frame sur {self.frame_skip})",
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"   📄 Résultats JSON: {output_path}")

    def _export_rally_clips(self):
        """Découpe la vidéo en clips individuels par rallye."""
        if not self.rallies:
            print("   ⚠️ Aucun rallye à découper")
            return

        clips_dir = os.path.join(self.output_dir, "rally_clips")
        os.makedirs(clips_dir, exist_ok=True)

        print(f"\n✂️  Découpage de {len(self.rallies)} rallyes en clips...")

        for rally in tqdm(self.rallies, desc="Découpage", unit="rallye"):
            clip_path = os.path.join(
                clips_dir,
                f"rally_{rally['rally_num']:03d}_{rally['start_time_str'].replace(':', '-')}_{rally['scored_by']}.mp4"
            )

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, rally['start_frame'])
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(clip_path, fourcc, self.fps,
                                  (self.frame_width, self.frame_height))

            for frame_idx in range(rally['start_frame'], rally['end_frame']):
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Ajouter des annotations sur le clip
                frame = self._annotate_frame(frame, frame_idx, rally)
                out.write(frame)

            out.release()

        print(f"   📁 Clips sauvegardés dans: {clips_dir}")

    def _annotate_frame(self, frame, frame_idx, rally):
        """Ajoute des annotations sur une frame (score, rotations, événements)."""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = min(w / 800, 1.5)
        thickness = max(1, int(font_scale * 2))

        # Bannière du score en haut
        score_left = rally.get('score_after', self.score).get(self.team_left, 0)
        score_right = rally.get('score_after', self.score).get(self.team_right, 0)
        score_text = f"{self.team_left} {score_left} - {score_right} {self.team_right}"

        text_size = cv2.getTextSize(score_text, font, font_scale, thickness)[0]
        text_x = (w - text_size[0]) // 2
        text_y = 40

        cv2.rectangle(frame, (text_x - 15, 5), (text_x + text_size[0] + 15, text_y + 10), (0, 0, 0), -1)
        cv2.putText(frame, score_text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

        # Rotations du passeur (en dessous du score)
        rot = rally.get('rotation', {})
        if rot:
            setter_text = f"Passeur: {rot.get('setter_left', '?')} | {rot.get('setter_right', '?')}"
            setter_size = cv2.getTextSize(setter_text, font, font_scale * 0.5, 1)[0]
            setter_x = (w - setter_size[0]) // 2
            setter_y = text_y + 30
            cv2.rectangle(frame, (setter_x - 10, setter_y - setter_size[1] - 5),
                          (setter_x + setter_size[0] + 10, setter_y + 5), (0, 0, 0), -1)
            cv2.putText(frame, setter_text, (setter_x, setter_y), font, font_scale * 0.5, (0, 200, 255), 1)

            # Indicateur de service
            serve_team = rot.get('serving_team', '')
            serve_text = f"Service: {serve_team}"
            cv2.putText(frame, serve_text, (10, setter_y), font, font_scale * 0.4, (200, 200, 200), 1)

        # Numéro du rallye
        rally_text = f"Rally #{rally['rally_num']}"
        cv2.putText(frame, rally_text, (10, h - 20), font, font_scale * 0.6, (255, 255, 255), max(1, thickness - 1))

        # Dessiner les détections de la frame courante (si analysée)
        if frame_idx in self.frame_index:
            idx = self.frame_index[frame_idx]
            frame_data = self.frame_actions[idx]
            for det in frame_data['detections']:
                bbox = det['bbox']
                action = det['action']
                conf = det['confidence']
                color = ACTION_COLORS.get(action, (255, 255, 255))

                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                label = f"{action} {conf:.1%}"
                label_size = cv2.getTextSize(label, font, font_scale * 0.5, 1)[0]
                cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 5), font, font_scale * 0.5, (255, 255, 255), 1)

        return frame

    # ==========================================================================
    # Pipeline complet
    # ==========================================================================

    def run(self):
        """Exécute le pipeline complet d'analyse."""
        print("=" * 60)
        print("🏐 CourtVision - Analyse de Volleyball")
        print("=" * 60)

        # Phase 1: Détection
        self.detect_actions()

        # Phase 2: Événements
        self.detect_events()

        # Phase 3: Rallyes, Score et Rotations
        self.detect_rallies()

        # Phase 4: Export
        self.export_results()

        # Résumé final
        state = self.rotation_tracker.get_state()
        print("\n" + "=" * 60)
        print("🏆 ANALYSE TERMINÉE")
        print("=" * 60)
        print(f"\n   📊 Score final: {self.team_left} {self.score[self.team_left]} - "
              f"{self.score[self.team_right]} {self.team_right}")
        print(f"   🏐 Rallyes: {len(self.rallies)}")
        print(f"   🎯 Événements: {len(self.events)}")
        print(f"   🔄 Passeur {self.team_left}: {state['setter_positions'][self.team_left]}")
        print(f"   🔄 Passeur {self.team_right}: {state['setter_positions'][self.team_right]}")
        print(f"   ⚡ Vitesse: {self.frame_skip}x (analysé 1 frame sur {self.frame_skip})")
        print(f"   📁 Résultats: {self.output_dir}/")
        print()

        self.cap.release()
        return self.rallies, self.score


# ==============================================================================
# Point d'entrée CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="🏐 CourtVision - Analyse automatique de vidéos de volleyball",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python analyze_video.py --video match.mp4
  python analyze_video.py --video match.mp4 --frame_skip 5 --conf 0.3
  python analyze_video.py --video match.mp4 --team_left "Paris" --team_right "Lyon" --gpu
  python analyze_video.py --video match.mp4 --setter_start_left P4 --setter_start_right P1 --first_serve left

Rotations du passeur:
  Les positions suivent l'ordre : P1 → P6 → P5 → P4 → P3 → P2 → P1...
  La rotation se fait quand l'équipe en réception gagne le point (side-out).
        """
    )

    parser.add_argument('--video', required=True, help="Chemin vers la vidéo de volleyball")
    parser.add_argument('--output_dir', default='Output', help="Dossier de sortie (défaut: Output)")
    parser.add_argument('--conf', type=float, default=0.4, help="Seuil de confiance (défaut: 0.4)")
    parser.add_argument('--frame_skip', type=int, default=5,
                        help="Analyser 1 frame sur N (défaut: 5, soit 5x plus rapide)")
    parser.add_argument('--imgsz', nargs=2, type=int, default=None,
                        help="Taille d'image pour l'inférence (ex: 1920 1080)")
    parser.add_argument('--gpu', action='store_true', help="Utiliser le GPU si disponible")
    parser.add_argument('--team_left', default="Équipe A", help="Nom de l'équipe côté gauche")
    parser.add_argument('--team_right', default="Équipe B", help="Nom de l'équipe côté droite")
    parser.add_argument('--setter_start_left', default='P1', choices=ROTATION_ORDER,
                        help="Position initiale du passeur équipe gauche (défaut: P1)")
    parser.add_argument('--setter_start_right', default='P1', choices=ROTATION_ORDER,
                        help="Position initiale du passeur équipe droite (défaut: P1)")
    parser.add_argument('--first_serve', default='left', choices=['left', 'right'],
                        help="Quelle équipe sert en premier (défaut: left)")

    args = parser.parse_args()

    # Vérifier que la vidéo existe
    if not os.path.exists(args.video):
        print(f"❌ Erreur: Vidéo non trouvée: {args.video}")
        sys.exit(1)

    # Lancer l'analyse
    analyzer = VolleyballAnalyzer(
        video_path=args.video,
        output_dir=args.output_dir,
        confidence=args.conf,
        img_size=args.imgsz,
        use_gpu=args.gpu,
        frame_skip=args.frame_skip,
        team_left=args.team_left,
        team_right=args.team_right,
        setter_start_left=args.setter_start_left,
        setter_start_right=args.setter_start_right,
        first_serve=args.first_serve,
    )

    analyzer.run()


if __name__ == '__main__':
    main()
