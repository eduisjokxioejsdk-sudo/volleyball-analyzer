#!/usr/bin/env python3
"""
CourtVision - Volleyball Video Analyzer (v2)
==============================================
Utilise volleyball_analytics (masouduut94) avec :
- VideoMAE  → classification de l'état du jeu (SERVICE / PLAY / NO_PLAY)
- YOLOv8    → détection d'actions (serve, spike, block, dig, set, receive)

Le découpage en points repose entièrement sur la machine à états VideoMAE :
  NO_PLAY → SERVICE  = début d'un nouveau point
  SERVICE → PLAY     = échange en cours
  PLAY    → NO_PLAY  = fin du point

Plus aucun filtre de durée, de déduplication ni de frame-skip maison.
"""

import os
import sys
import json
import argparse
import warnings
from datetime import timedelta
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Ajouter le dossier courant au PYTHONPATH pour que `from ml_manager import …`
# fonctionne quand on est dans le répertoire volleyball-analyzer
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_manager import MLManager, ModelWeightsConfig, GameState


# ===========================================================================
# Configuration
# ===========================================================================

CLASSIFICATION_INTERVAL = 30   # Classifier le game-state toutes les N frames
ACTION_DETECTION_INTERVAL = 5  # Détecter les actions toutes les N frames
FRAME_CENTER_RATIO = 0.5       # Ratio pour séparer gauche/droite du terrain
MIN_RALLY_DURATION = 3.0       # Durée min (s) pour garder un rallye

# Rotations du passeur (P1→P6→P5→P4→P3→P2)
ROTATION_ORDER = ['P1', 'P6', 'P5', 'P4', 'P3', 'P2']


# ===========================================================================
# Gestionnaire de Rotations
# ===========================================================================

class RotationTracker:
    """Suit les rotations du passeur pour chaque équipe."""

    def __init__(self, team_left, team_right,
                 setter_start_left='P1', setter_start_right='P1',
                 first_serve='left'):
        self.team_left = team_left
        self.team_right = team_right
        self.rotation_index = {
            team_left: ROTATION_ORDER.index(setter_start_left),
            team_right: ROTATION_ORDER.index(setter_start_right),
        }
        self.serving_team = team_left if first_serve == 'left' else team_right
        self.history = []

    def get_setter_position(self, team):
        return ROTATION_ORDER[self.rotation_index[team]]

    def get_serving_team(self):
        return self.serving_team

    def get_receiving_team(self):
        return self.team_right if self.serving_team == self.team_left else self.team_left

    def process_point(self, scored_by, rally_num=0):
        receiving_team = self.get_receiving_team()
        rotated = False
        rotation_team = None
        if scored_by == receiving_team:
            self.serving_team = scored_by
            self.rotation_index[scored_by] = (self.rotation_index[scored_by] + 1) % len(ROTATION_ORDER)
            rotated = True
            rotation_team = scored_by
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

    def get_state(self):
        return {
            'serving_team': self.serving_team,
            'setter_positions': {
                self.team_left: self.get_setter_position(self.team_left),
                self.team_right: self.get_setter_position(self.team_right),
            }
        }


# ===========================================================================
# Analyseur principal
# ===========================================================================

class VolleyballAnalyzer:
    """Analyse une vidéo de volleyball avec VideoMAE + YOLO."""

    def __init__(self, video_path, output_dir="Output",
                 team_left="Équipe A", team_right="Équipe B",
                 setter_start_left='P1', setter_start_right='P1',
                 first_serve='left', use_gpu=False):

        self.video_path = video_path
        self.output_dir = output_dir
        self.team_left = team_left
        self.team_right = team_right

        # Résultats
        self.rallies = []
        self.score = {team_left: 0, team_right: 0}

        # Rotations
        self.rotation_tracker = RotationTracker(
            team_left, team_right,
            setter_start_left, setter_start_right, first_serve
        )

        # Ouvrir la vidéo
        self._open_video()

        # Charger le MLManager
        self._load_models(use_gpu)

    def _open_video(self):
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Impossible d'ouvrir la vidéo: {self.video_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        print(f"\n🎬 Vidéo: {os.path.basename(self.video_path)}")
        print(f"   Résolution: {self.frame_width}x{self.frame_height}")
        print(f"   FPS: {self.fps:.1f} | Frames: {self.total_frames}")
        print(f"   Durée: {timedelta(seconds=int(self.duration))}")

    def _load_models(self, use_gpu):
        device = "cuda" if use_gpu else "cpu"
        print(f"\n📦 Chargement du MLManager (device={device})...")
        print("   Les poids seront auto-téléchargés si absents.")
        self.ml = MLManager(device=device)
        status = self.ml.get_model_status()
        for name, info in status.items():
            emoji = "✅" if info.get('available') else "❌"
            print(f"   {emoji} {name}")

    def frame_to_time(self, frame_num):
        return frame_num / self.fps if self.fps > 0 else 0

    def time_to_str(self, seconds):
        return str(timedelta(seconds=round(seconds, 1)))[2:10]

    # ======================================================================
    # Pipeline principal
    # ======================================================================

    def run(self, progress_callback=None):
        """Exécute le pipeline complet."""
        print("\n" + "=" * 60)
        print("🏐 CourtVision v2 — Analyse avec VideoMAE + YOLO")
        print("=" * 60)

        # Phase 1 : Parcourir la vidéo, classifier le game-state, détecter les actions
        raw_rallies = self._scan_video(progress_callback)

        # Phase 2 : Filtrer & construire les rallyes
        self._build_rallies(raw_rallies)

        # Phase 3 : Scoring + rotations
        self._attribute_scores_and_rotations()

        # Phase 4 : Export
        self._export_json()

        # Résumé
        state = self.rotation_tracker.get_state()
        print("\n" + "=" * 60)
        print("🏆 ANALYSE TERMINÉE")
        print("=" * 60)
        print(f"   📊 Score: {self.team_left} {self.score[self.team_left]} - "
              f"{self.score[self.team_right]} {self.team_right}")
        print(f"   🏐 Points: {len(self.rallies)}")
        print(f"   🔄 Passeur {self.team_left}: {state['setter_positions'][self.team_left]}")
        print(f"   🔄 Passeur {self.team_right}: {state['setter_positions'][self.team_right]}")
        print(f"   📁 Résultats: {self.output_dir}/")
        print()

        self.cap.release()
        return self.rallies, self.score

    # ======================================================================
    # Phase 1 : Scan de la vidéo (game-state + actions)
    # ======================================================================

    def _scan_video(self, progress_callback=None):
        """
        Parcourt chaque frame :
        - Toutes les CLASSIFICATION_INTERVAL frames → classify_game_state (VideoMAE)
        - Toutes les ACTION_DETECTION_INTERVAL frames pendant SERVICE/PLAY → detect_actions
        
        Retourne une liste de raw_rallies = [{ start_frame, end_frame, actions: [...] }]
        """
        print(f"\n🔍 Phase 1 : Scan vidéo (game-state toutes les {CLASSIFICATION_INTERVAL} frames)...")
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        frame_buffer = []          # Buffer de 30 frames pour VideoMAE
        current_state = GameState.NO_PLAY
        prev_state = GameState.NO_PLAY

        raw_rallies = []           # Liste de rallyes bruts
        current_rally = None       # Rallye en cours de construction

        frame_num = 0
        last_reported_pct = -1

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame_buffer.append(frame)
            if len(frame_buffer) > CLASSIFICATION_INTERVAL:
                frame_buffer = frame_buffer[-CLASSIFICATION_INTERVAL:]

            # --- Classification du game-state ---
            if frame_num % CLASSIFICATION_INTERVAL == 0 and len(frame_buffer) >= 16:
                try:
                    result = self.ml.classify_game_state(frame_buffer)
                    new_state = result.predicted_class
                    confidence = result.confidence
                except Exception as e:
                    new_state = current_state
                    confidence = 0.0

                prev_state = current_state
                current_state = new_state

                # --- Machine à états ---
                # Transition vers SERVICE ou PLAY = début d'un nouveau point
                if current_state in (GameState.SERVICE, GameState.PLAY) and prev_state == GameState.NO_PLAY:
                    if current_rally is not None:
                        # Fermer le rallye précédent (ne devrait pas arriver, mais sécurité)
                        current_rally['end_frame'] = frame_num
                        raw_rallies.append(current_rally)
                    current_rally = {
                        'start_frame': frame_num,
                        'end_frame': None,
                        'actions': [],
                        'states': [(frame_num, str(current_state), confidence)],
                    }

                # Transition vers NO_PLAY = fin du point
                elif current_state == GameState.NO_PLAY and prev_state in (GameState.SERVICE, GameState.PLAY):
                    if current_rally is not None:
                        current_rally['end_frame'] = frame_num
                        raw_rallies.append(current_rally)
                        current_rally = None

                # Enregistrer l'état dans le rallye en cours
                if current_rally is not None:
                    current_rally['states'].append((frame_num, str(current_state), confidence))

            # --- Détection d'actions pendant SERVICE/PLAY ---
            if current_rally is not None and frame_num % ACTION_DETECTION_INTERVAL == 0:
                if current_state in (GameState.SERVICE, GameState.PLAY):
                    try:
                        action_dets = self.ml.detect_actions(frame, conf_threshold=0.30)
                        for det in action_dets:
                            center_x, center_y = det.bbox.center
                            side = 'left' if center_x < self.frame_width * FRAME_CENTER_RATIO else 'right'
                            current_rally['actions'].append({
                                'frame': frame_num,
                                'time': self.frame_to_time(frame_num),
                                'action': det.class_name,
                                'confidence': det.confidence,
                                'side': side,
                                'center': [center_x, center_y],
                            })
                    except Exception:
                        pass

            frame_num += 1

            # Progress callback
            if progress_callback and self.total_frames > 0:
                pct = int((frame_num / self.total_frames) * 100)
                if pct != last_reported_pct and pct % 2 == 0:
                    last_reported_pct = pct
                    try:
                        progress_callback(pct)
                    except Exception:
                        pass

            # Log périodique
            if frame_num % (self.fps * 30) < 1:  # ~toutes les 30s
                t = self.time_to_str(self.frame_to_time(frame_num))
                print(f"   ⏱️  {t} | état={current_state} | rallyes trouvés={len(raw_rallies)}")

        # Fermer le dernier rallye si besoin
        if current_rally is not None:
            current_rally['end_frame'] = frame_num
            raw_rallies.append(current_rally)

        print(f"\n   ✅ {frame_num} frames analysées, {len(raw_rallies)} rallyes bruts détectés")
        return raw_rallies

    # ======================================================================
    # Phase 2 : Construction des rallyes filtrés
    # ======================================================================

    def _build_rallies(self, raw_rallies):
        """Filtre et structure les rallyes."""
        print(f"\n🏐 Phase 2 : Filtrage des {len(raw_rallies)} rallyes bruts...")
        self.rallies = []

        for rr in raw_rallies:
            start = rr['start_frame']
            end = rr['end_frame'] if rr['end_frame'] else self.total_frames
            duration = (end - start) / self.fps if self.fps > 0 else 0

            # Filtre de durée minimale
            if duration < MIN_RALLY_DURATION:
                continue

            # Déterminer le côté du service
            serve_actions = [a for a in rr['actions'] if a['action'] in ('serve', 'service')]
            serve_side = serve_actions[0]['side'] if serve_actions else 'unknown'

            rally = {
                'rally_num': len(self.rallies) + 1,
                'start_frame': start,
                'end_frame': end,
                'start_time': self.frame_to_time(start),
                'end_time': self.frame_to_time(end),
                'start_time_str': self.time_to_str(self.frame_to_time(start)),
                'end_time_str': self.time_to_str(self.frame_to_time(end)),
                'duration': round(duration, 1),
                'actions': rr['actions'],
                'serve_side': serve_side,
                'scored_by': None,
                'score_after': {},
                'rotation': {},
            }
            self.rallies.append(rally)

            print(f"   Point {rally['rally_num']}: "
                  f"{rally['start_time_str']}-{rally['end_time_str']} "
                  f"({rally['duration']}s, {len(rr['actions'])} actions)")

        print(f"   ✅ {len(self.rallies)} points retenus")

    # ======================================================================
    # Phase 3 : Scoring + Rotations
    # ======================================================================

    def _attribute_scores_and_rotations(self):
        """Attribue le score et met à jour les rotations."""
        print(f"\n🎯 Phase 3 : Attribution du score et des rotations...")
        self.score = {self.team_left: 0, self.team_right: 0}

        for rally in self.rallies:
            actions = rally['actions']
            if not actions:
                rally['scored_by'] = 'unknown'
                rally['rotation'] = self.rotation_tracker.get_state()
                continue

            # Heuristique : dernière action offensive
            last_offensive = None
            for a in reversed(actions):
                if a['action'] in ('spike', 'block'):
                    last_offensive = a
                    break

            if last_offensive:
                rally['scored_by'] = self.team_left if last_offensive['side'] == 'left' else self.team_right
            else:
                # Dernière action
                last = actions[-1]
                if last['action'] in ('dig', 'defense', 'receive', 'reception'):
                    rally['scored_by'] = self.team_right if last['side'] == 'left' else self.team_left
                elif last['action'] in ('serve', 'service'):
                    rally['scored_by'] = self.team_left if last['side'] == 'left' else self.team_right
                else:
                    rally['scored_by'] = self.team_left if last['side'] == 'left' else self.team_right

            # Score
            if rally['scored_by'] in self.score:
                self.score[rally['scored_by']] += 1
            rally['score_after'] = dict(self.score)

            # Rotation
            rot = self.rotation_tracker.process_point(rally['scored_by'], rally['rally_num'])
            rally['rotation'] = {
                'serving_team': rot['serving_team'],
                'rotated': rot['rotated'],
                'rotation_team': rot['rotation_team'],
                'setter_left': rot['setter_left'],
                'setter_right': rot['setter_right'],
            }

        # Affichage
        print(f"\n📋 Résultats point par point:")
        for r in self.rallies:
            rot = r.get('rotation', {})
            sa = r.get('score_after', {})
            score_str = f"{sa.get(self.team_left, 0)}-{sa.get(self.team_right, 0)}"
            print(f"   #{r['rally_num']:>2} | {r['start_time_str']}-{r['end_time_str']} | "
                  f"{r['scored_by']:<12} | {score_str:<6} | "
                  f"srv={rot.get('serving_team', '?'):<10}")

    # ======================================================================
    # Phase 4 : Export JSON
    # ======================================================================

    def _export_json(self):
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "analysis_results.json")

        state = self.rotation_tracker.get_state()
        results = {
            'video': {
                'path': self.video_path,
                'filename': os.path.basename(self.video_path),
                'fps': self.fps,
                'total_frames': self.total_frames,
                'width': self.frame_width,
                'height': self.frame_height,
                'duration': self.duration,
                'duration_str': str(timedelta(seconds=int(self.duration))),
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
                    'actions': r['actions'],
                }
                for r in self.rallies
            ],
            'statistics': {
                'total_rallies': len(self.rallies),
                'avg_rally_duration': float(np.mean([r['duration'] for r in self.rallies])) if self.rallies else 0,
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n   📄 JSON exporté: {output_path}")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="🏐 CourtVision v2 — VideoMAE + YOLO")
    parser.add_argument('--video', required=True)
    parser.add_argument('--output_dir', default='Output')
    parser.add_argument('--gpu', action='store_true')
    parser.add_argument('--team_left', default="Équipe A")
    parser.add_argument('--team_right', default="Équipe B")
    parser.add_argument('--setter_start_left', default='P1', choices=ROTATION_ORDER)
    parser.add_argument('--setter_start_right', default='P1', choices=ROTATION_ORDER)
    parser.add_argument('--first_serve', default='left', choices=['left', 'right'])
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"❌ Vidéo non trouvée: {args.video}")
        sys.exit(1)

    analyzer = VolleyballAnalyzer(
        video_path=args.video,
        output_dir=args.output_dir,
        team_left=args.team_left,
        team_right=args.team_right,
        setter_start_left=args.setter_start_left,
        setter_start_right=args.setter_start_right,
        first_serve=args.first_serve,
        use_gpu=args.gpu,
    )
    analyzer.run()


if __name__ == '__main__':
    main()
